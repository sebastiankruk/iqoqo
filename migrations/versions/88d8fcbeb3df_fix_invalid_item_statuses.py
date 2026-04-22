"""fix_invalid_item_statuses

Revision ID: 88d8fcbeb3df
Revises: 51a5cbb508f8
Create Date: 2026-04-22 23:18:57.437234

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '88d8fcbeb3df'
down_revision = '51a5cbb508f8'
branch_labels = None
depends_on = None


def upgrade():
    # Reflection for the required tables
    bind = op.get_bind()
    meta = sa.MetaData()
    
    # Define tables with their schemas
    items_table = sa.Table(
        'items', meta,
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('manifestation_id', sa.Integer),
        sa.Column('status', sa.String(50)),
        sa.Column('collection_status', sa.String(50)),
        schema='inventory'
    )
    
    expressions_table = sa.Table(
        'expressions', meta,
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('content_type', sa.String(50)),
        schema='catalog'
    )
    
    manifestations_table = sa.Table(
        'manifestations', meta,
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('expression_id', sa.Integer),
        schema='catalog'
    )

    # Canonical mapping for valid statuses per category
    CATEGORY_PROGRESS = {
        'text': {'want_to_read', 'reading', 'read'},
        'music': {'want_to_listen', 'listening', 'listened'},
        'movie': {'want_to_watch', 'watching', 'watched'},
        'board_game': {'want_to_play', 'playing', 'played'},
        'puzzle': {'want_to_play', 'playing', 'played'},
    }
    
    CATEGORY_DEFAULTS = {
        'text': 'want_to_read',
        'music': 'want_to_listen',
        'movie': 'want_to_watch',
        'board_game': 'want_to_play',
        'puzzle': 'want_to_play',
    }
    
    COLLECTION_STATUSES = {'wish_list', 'ordered', 'available', 'lent', 'damaged', 'lost'}

    # Fetch all items that might need fixing
    items = bind.execute(
        sa.select(
            items_table.c.id,
            items_table.c.status,
            items_table.c.collection_status,
            expressions_table.c.content_type
        ).select_from(
            items_table.join(
                manifestations_table, items_table.c.manifestation_id == manifestations_table.c.id
            ).join(
                expressions_table, manifestations_table.c.expression_id == expressions_table.c.id
            )
        )
    ).all()

    for item_id, status, coll_status, content_type in items:
        new_status = None
        new_coll_status = None
        
        ct = content_type or 'text'
        valid_for_category = CATEGORY_PROGRESS.get(ct, set())
        
        # Rule 1: 'unread' is always 'want_to_read' (legacy fix)
        if status == 'unread':
            new_status = CATEGORY_DEFAULTS.get(ct, 'want_to_read')
            
        # Rule 2: 'available' in status field is a bug
        elif status == 'available':
            new_coll_status = 'available'
            new_status = CATEGORY_DEFAULTS.get(ct, 'want_to_read')
            
        # Rule 3: If status is a collection status, move it if coll_status is empty/default
        elif status in COLLECTION_STATUSES:
            new_coll_status = status
            new_status = CATEGORY_DEFAULTS.get(ct, 'want_to_read')
            
        # Rule 4: If status is a progress status but for the WRONG category
        elif status not in valid_for_category:
            # It might be a valid status for ANOTHER category (like 'want_to_read' for music)
            # Map it to the corresponding status in the correct category if possible
            if 'read' in status or 'watch' in status or 'listen' in status or 'play' in status:
                # Heuristic mapping: want_to_X -> want_to_Y, X-ing -> Y-ing, X-ed -> Y-ed
                prefix = 'want_to_' if 'want_to_' in status else ''
                suffix = 'ing' if status.endswith('ing') else ('ed' if status.endswith('ed') else '')
                
                if prefix:
                    new_status = CATEGORY_DEFAULTS.get(ct)
                elif suffix == 'ing':
                    # reading, listening, watching, playing
                    if ct == 'text': new_status = 'reading'
                    elif ct == 'music': new_status = 'listening'
                    elif ct == 'movie': new_status = 'watching'
                    else: new_status = 'playing'
                elif suffix == 'ed':
                    # read, listened, watched, played
                    if ct == 'text': new_status = 'read'
                    elif ct == 'music': new_status = 'listened'
                    elif ct == 'movie': new_status = 'watched'
                    else: new_status = 'played'
                else:
                    new_status = CATEGORY_DEFAULTS.get(ct)
            else:
                new_status = CATEGORY_DEFAULTS.get(ct)
            
        # Apply updates if needed
        if (new_status and new_status != status) or (new_coll_status and new_coll_status != coll_status):
            stmt = sa.update(items_table).where(items_table.c.id == item_id)
            if new_status and new_status != status:
                stmt = stmt.values(status=new_status)
            if new_coll_status and new_coll_status != coll_status:
                stmt = stmt.values(collection_status=new_coll_status)
            bind.execute(stmt)


def downgrade():
    # Data migrations are generally not reversible without backups
    pass
