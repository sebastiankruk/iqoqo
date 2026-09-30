## MODIFIED Requirements

### Requirement: Streaming RDF Serialization for Large Collections

The system SHALL provide a generator-based streaming RDF serialization interface that yields serialized RDF chunks without requiring the entire graph of a large collection to reside concurrently in memory. The system SHALL ensure that JSON-LD streaming produces a single valid document using the `@graph` container, even when chunks are concatenated across HTTP responses. Fallback handling for unparseable chunks SHALL not produce malformed JSON mid-stream.

#### Scenario: Streaming collection export

- **WHEN** streaming serialization is invoked for a collection containing numerous items
- **THEN** the serialization function yields chunks of serialized triples iteratively, enabling HTTP chunked transfer responses without high memory spikes.

#### Scenario: JSON-LD streaming across multiple chunks

- **WHEN** a JSON-LD export spans multiple chunks due to collection size
- **THEN** the concatenated response SHALL be a single valid JSON-LD document with a `@graph` container, parseable by standard JSON-LD processors

#### Scenario: Unparseable chunk during streaming

- **WHEN** a chunk fails to parse during streaming serialization
- **THEN** the system SHALL either skip the chunk with a logged warning or produce a valid partial document, but SHALL NOT produce malformed JSON that breaks the entire response

## ADDED Requirements

### Requirement: Multi-Chunk Streaming Validation

The system SHALL provide end-to-end tests that verify streaming RDF serialization produces valid output when the response spans multiple chunks, particularly for JSON-LD format.

#### Scenario: Public RDF streaming with multiple chunks

- **WHEN** a public RDF export returns a response larger than a single chunk
- **THEN** an end-to-end test SHALL verify the concatenated response is valid JSON-LD, Turtle, or N-Triples (depending on format) and can be parsed without errors
