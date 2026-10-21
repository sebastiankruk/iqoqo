# Copyright (C) 2026 Sebastian Ryszard Kruk (dev@kruk.me)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>
#
"""SHACL and RDF validation tests for social and ActivityStreams/CIDOC CRM ontology mappings."""

import datetime
from pathlib import Path
from typing import cast

import pytest

pyshacl = pytest.importorskip("pyshacl")
rdflib = pytest.importorskip("rdflib")

from rdflib import Graph, Literal, Namespace, URIRef  # noqa: E402
from rdflib.namespace import RDF, XSD  # noqa: E402

from app.api.public_rdf import (  # noqa: E402
    serialize_custody_events_to_rdf,
    serialize_loan_request_to_rdf,
    serialize_user_collection_to_rdf,
    serialize_user_followers_to_rdf,
    serialize_user_intents_to_rdf,
)
from app.db.federation import FederationActor, FederationFollower, FederationInstance, FollowStatus  # noqa: E402
from app.db.models import (  # noqa: E402
    Expression,
    Item,
    ItemCustodyEvent,
    LoanRequest,
    Manifestation,
    User,
    UserCollection,
    UserCollectionItem,
    UserWorkIntent,
    Work,
    db,
)

ROOT = Path(__file__).resolve().parents[1]
IQOQO = Namespace("https://iqoqo.org/ontology#")
AS = Namespace("https://www.w3.org/ns/activitystreams#")
CRM = Namespace("http://www.cidoc-crm.org/cidoc-crm/")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
SCHEMA = Namespace("https://schema.org/")

_SHAPES_PATH = ROOT / "docs" / "ontology" / "iqoqo-shapes.ttl"
_ONTOLOGY_PATH = ROOT / "docs" / "ontology" / "iqoqo.ttl"


def _parse_cached_graph(path: Path) -> Graph:
    g = Graph()
    g.parse(str(path), format="turtle")
    return g


_CACHED_SHAPES = _parse_cached_graph(_SHAPES_PATH)
_CACHED_ONTOLOGY = _parse_cached_graph(_ONTOLOGY_PATH)


def _validate_with_shacl(data_graph: Graph) -> tuple[bool, Graph, str]:
    """Validates data graph against iqoqo-shapes.ttl with RDFS inference."""
    shapes = Graph() + _CACHED_SHAPES
    ont = Graph() + _CACHED_ONTOLOGY
    return cast(
        "tuple[bool, Graph, str]",
        pyshacl.validate(
            data_graph=data_graph,
            shacl_graph=shapes,
            ont_graph=ont,
            inference="rdfs",
            abort_on_first=False,
        ),
    )


class TestSocialOntologySHACL:
    """Tests SHACL compliance of social entities mapped to ActivityStreams & CIDOC CRM."""

    def test_item_custody_loan_as_cidoc_e10_conforms(self) -> None:
        """Scenario: Custody loan serialized as CIDOC E10 validates against iqoqo-shapes.ttl."""
        g = Graph()
        g.bind("iqoqo", IQOQO)
        g.bind("crm", CRM)
        g.bind("as", AS)

        item_uri = URIRef("https://iqoqo.org/item/42")
        g.add((item_uri, RDF.type, IQOQO.Item))

        custody_uri = URIRef("https://iqoqo.org/custody/101")
        g.add((custody_uri, RDF.type, IQOQO.ItemCustodyEvent))
        g.add((custody_uri, RDF.type, CRM.E10_Transfer_of_Custody))
        g.add((custody_uri, RDF.type, AS.Accept))
        g.add((custody_uri, IQOQO.custodyItem, item_uri))
        g.add((custody_uri, IQOQO.eventType, Literal("loan", datatype=XSD.string)))
        g.add((custody_uri, IQOQO.recordedAt, Literal("2026-10-21T12:00:00Z", datatype=XSD.dateTime)))

        conforms, _, results_text = _validate_with_shacl(g)
        assert conforms, f"Custody event graph should conform to SHACL. Violations:\n{results_text}"

    def test_item_custody_loan_missing_recorded_at_fails(self) -> None:
        """Custody event missing recordedAt violates ItemCustodyEventShape."""
        g = Graph()
        item_uri = URIRef("https://iqoqo.org/item/42")
        g.add((item_uri, RDF.type, IQOQO.Item))

        custody_uri = URIRef("https://iqoqo.org/custody/102")
        g.add((custody_uri, RDF.type, IQOQO.ItemCustodyEvent))
        g.add((custody_uri, RDF.type, CRM.E10_Transfer_of_Custody))
        g.add((custody_uri, IQOQO.custodyItem, item_uri))
        g.add((custody_uri, IQOQO.eventType, Literal("loan", datatype=XSD.string)))
        # Missing recordedAt

        conforms, _, results_text = _validate_with_shacl(g)
        assert not conforms
        assert "recordedAt" in results_text

    def test_user_collection_as_ordered_collection_conforms(self) -> None:
        """UserCollection mapped to as:OrderedCollection conforms to UserCollectionShape."""
        g = Graph()
        user_uri = URIRef("https://iqoqo.org/u/alice")
        g.add((user_uri, RDF.type, IQOQO.User))

        coll_uri = URIRef("https://iqoqo.org/collections/7")
        g.add((coll_uri, RDF.type, IQOQO.UserCollection))
        g.add((coll_uri, RDF.type, AS.OrderedCollection))
        g.add((coll_uri, IQOQO.collectionOwner, user_uri))
        g.add((coll_uri, IQOQO.collectionName, Literal("Sci-Fi Classics", datatype=XSD.string)))

        conforms, _, results_text = _validate_with_shacl(g)
        assert conforms, f"UserCollection graph should conform. Violations:\n{results_text}"

    def test_user_collection_missing_name_fails(self) -> None:
        """UserCollection missing collectionName violates UserCollectionShape."""
        g = Graph()
        user_uri = URIRef("https://iqoqo.org/u/alice")
        g.add((user_uri, RDF.type, IQOQO.User))

        coll_uri = URIRef("https://iqoqo.org/collections/8")
        g.add((coll_uri, RDF.type, IQOQO.UserCollection))
        g.add((coll_uri, RDF.type, AS.OrderedCollection))
        g.add((coll_uri, IQOQO.collectionOwner, user_uri))
        # Missing collectionName

        conforms, _, results_text = _validate_with_shacl(g)
        assert not conforms
        assert "collectionName" in results_text

    def test_user_work_intent_as_want_action_conforms(self) -> None:
        """UserWorkIntent mapped to schema:WantAction conforms to UserWorkIntentShape."""
        g = Graph()
        user_uri = URIRef("https://iqoqo.org/u/bob")
        g.add((user_uri, RDF.type, IQOQO.User))

        work_uri = URIRef("https://iqoqo.org/work/99")
        g.add((work_uri, RDF.type, IQOQO.Work))

        intent_uri = URIRef("https://iqoqo.org/intent/12")
        g.add((intent_uri, RDF.type, IQOQO.UserWorkIntent))
        g.add((intent_uri, RDF.type, SCHEMA.WantAction))
        g.add((intent_uri, IQOQO.intentUser, user_uri))
        g.add((intent_uri, IQOQO.intentWork, work_uri))
        g.add((intent_uri, IQOQO.intentStatus, Literal("want_to_read", datatype=XSD.string)))

        conforms, _, results_text = _validate_with_shacl(g)
        assert conforms, f"UserWorkIntent graph should conform. Violations:\n{results_text}"

    def test_federation_follower_as_follow_conforms(self) -> None:
        """FederationFollower mapped to as:Follow conforms to FederationFollowerShape."""
        g = Graph()
        user_uri = URIRef("https://iqoqo.org/u/charlie")
        g.add((user_uri, RDF.type, IQOQO.User))

        follow_uri = URIRef("https://iqoqo.org/followers/5")
        g.add((follow_uri, RDF.type, IQOQO.FederationFollower))
        g.add((follow_uri, RDF.type, AS.Follow))
        g.add((follow_uri, IQOQO.followerLocalUser, user_uri))
        g.add((follow_uri, IQOQO.followerStatus, Literal("accepted", datatype=XSD.string)))

        conforms, _, results_text = _validate_with_shacl(g)
        assert conforms, f"FederationFollower graph should conform. Violations:\n{results_text}"

    def test_loan_request_as_offer_conforms(self) -> None:
        """LoanRequest mapped to as:Offer conforms to LoanRequestShape."""
        g = Graph()
        item_uri = URIRef("https://iqoqo.org/item/50")
        g.add((item_uri, RDF.type, IQOQO.Item))

        user_uri = URIRef("https://iqoqo.org/u/dave")
        g.add((user_uri, RDF.type, IQOQO.User))

        loan_uri = URIRef("https://iqoqo.org/loans/15")
        g.add((loan_uri, RDF.type, IQOQO.LoanRequest))
        g.add((loan_uri, RDF.type, AS.Offer))
        g.add((loan_uri, IQOQO.loanItem, item_uri))
        g.add((loan_uri, IQOQO.loanRequester, user_uri))
        g.add((loan_uri, IQOQO.loanStatus, Literal("pending", datatype=XSD.string)))

        conforms, _, results_text = _validate_with_shacl(g)
        assert conforms, f"LoanRequest graph should conform. Violations:\n{results_text}"


class TestPublicRDFSocialEndpoints:
    """Tests public RDF endpoints for social entities."""

    @pytest.fixture
    def social_test_data(self, app):
        with app.app_context():
            user = User(
                email="social_public@iqoqo.local",
                display_name="Social Star",
                visibility="public",
                public_username="socialstar",
            )
            user.set_password("valid-pass-123")
            db.session.add(user)
            db.session.flush()

            work = Work(title="Dune Chronology")
            db.session.add(work)
            db.session.flush()

            expr = Expression(work_id=work.id, content_type="book", language="en")
            db.session.add(expr)
            db.session.flush()

            manif = Manifestation(expression_id=expr.id, isbn13="9780441013593")
            db.session.add(manif)
            db.session.flush()

            item = Item(owner_id=user.id, manifestation_id=manif.id, status="available", is_hidden=False)
            db.session.add(item)
            db.session.flush()

            custody_event = ItemCustodyEvent(
                item_id=item.id,
                actor_id=user.id,
                event_type="loan",
                notes="Lent copy to reader friend",
                recorded_at=datetime.datetime.now(datetime.UTC),
            )
            db.session.add(custody_event)

            coll = UserCollection(owner_id=user.id, name="My Sci-Fi Favorites")
            db.session.add(coll)
            db.session.flush()

            coll_item = UserCollectionItem(collection_id=coll.id, item_id=item.id)
            db.session.add(coll_item)

            intent = UserWorkIntent(user_id=user.id, work_id=work.id, status="want_to_read", is_hidden=False)
            db.session.add(intent)

            instance = FederationInstance(
                domain="remote.library",
                shared_inbox_url="https://remote.library/inbox",
                software_name="iqoqo",
                trust_level="trusted",
            )
            db.session.add(instance)
            db.session.flush()

            actor = FederationActor(
                actor_uri="https://remote.library/users/remotereader",
                inbox_url="https://remote.library/users/remotereader/inbox",
                username="remotereader",
                instance_id=instance.id,
            )
            db.session.add(actor)
            db.session.flush()

            follower = FederationFollower(local_user_id=user.id, remote_actor_id=actor.id, status=FollowStatus.ACCEPTED)
            db.session.add(follower)

            db.session.commit()

            return {
                "user_id": user.id,
                "username": user.public_username,
                "item_id": item.id,
                "custody_id": custody_event.id,
                "collection_id": coll.id,
                "work_id": work.id,
                "intent_id": intent.id,
            }

    def test_get_public_item_custody_rdf(self, client, social_test_data) -> None:
        """GET /api/public/items/<id>/custody returns CIDOC CRM E10 RDF conforming to SHACL."""
        item_id = social_test_data["item_id"]
        response = client.get(f"/api/public/items/{item_id}/custody?format=turtle")
        assert response.status_code == 200
        assert "text/turtle" in response.headers["Content-Type"]

        rdf_text = response.data.decode("utf-8")
        assert "E10_Transfer_of_Custody" in rdf_text
        assert "ItemCustodyEvent" in rdf_text

        # Validate with pyshacl
        g = Graph()
        g.parse(data=rdf_text, format="turtle")
        conforms, _, results_text = _validate_with_shacl(g)
        assert conforms, f"Exported custody RDF should validate against SHACL. Violations:\n{results_text}"

    def test_get_public_collection_rdf(self, client, social_test_data) -> None:
        """GET /api/public/collections/<id> returns ActivityStreams OrderedCollection RDF conforming to SHACL."""
        coll_id = social_test_data["collection_id"]
        response = client.get(f"/api/public/collections/{coll_id}?format=turtle")
        assert response.status_code == 200
        assert "text/turtle" in response.headers["Content-Type"]

        rdf_text = response.data.decode("utf-8")
        assert "OrderedCollection" in rdf_text
        assert "UserCollection" in rdf_text

        g = Graph()
        g.parse(data=rdf_text, format="turtle")
        conforms, _, results_text = _validate_with_shacl(g)
        assert conforms, f"Exported collection RDF should validate against SHACL. Violations:\n{results_text}"

    def test_get_public_user_wishlist_rdf(self, client, social_test_data) -> None:
        """GET /api/public/u/<username>/wishlist returns Schema.org WantAction RDF conforming to SHACL."""
        username = social_test_data["username"]
        response = client.get(f"/api/public/u/{username}/wishlist?format=turtle")
        assert response.status_code == 200

        rdf_text = response.data.decode("utf-8")
        assert "WantAction" in rdf_text
        assert "UserWorkIntent" in rdf_text

        g = Graph()
        g.parse(data=rdf_text, format="turtle")
        conforms, _, results_text = _validate_with_shacl(g)
        assert conforms, f"Exported wishlist RDF should validate against SHACL. Violations:\n{results_text}"

    def test_get_public_user_followers_rdf(self, client, social_test_data) -> None:
        """GET /api/public/u/<username>/followers returns ActivityStreams Follow RDF conforming to SHACL."""
        username = social_test_data["username"]
        response = client.get(f"/api/public/u/{username}/followers?format=turtle")
        assert response.status_code == 200

        rdf_text = response.data.decode("utf-8")
        assert "Follow" in rdf_text
        assert "FederationFollower" in rdf_text

        g = Graph()
        g.parse(data=rdf_text, format="turtle")
        conforms, _, results_text = _validate_with_shacl(g)
        assert conforms, f"Exported followers RDF should validate against SHACL. Violations:\n{results_text}"

    def test_public_custody_hidden_item_returns_404(self, client, app, social_test_data) -> None:
        """Hidden item custody cannot be dereferenced publicly."""
        with app.app_context():
            item = db.session.get(Item, social_test_data["item_id"])
            item.is_hidden = True
            db.session.commit()

        response = client.get(f"/api/public/items/{social_test_data['item_id']}/custody")
        assert response.status_code == 404
