//
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Contact Book backend: a Spring Boot REST API for CRUD on contacts, backed by a
pluggable storage layer (currently a JSON file). Java 25, Spring Boot 4.1.0,
Maven. There is no Maven wrapper checked in — use a locally installed `mvn`.

## Commands

```bash
mvn spring-boot:run           # run the API on http://localhost:8080
mvn test                      # run all tests
mvn package                   # build the runnable jar into target/
mvn spring-boot:run -Dspring-boot.run.arguments=--contactbook.storage.file=/tmp/contacts.json

# run a single test class / method
mvn test -Dtest=ContactControllerTest
mvn test -Dtest=ContactControllerTest#create_returns201WithLocationAndBody
```

The API is at `/api/contacts` (GET list, GET `/{id}`, POST, PUT `/{id}`, DELETE `/{id}`).

## Architecture

Classic layered Spring MVC. The dependency direction is web → service →
repository, and each layer speaks only to the one below it through the `Contact`
domain record.

- **`domain/Contact`** — immutable `record` shared across all layers. `id` is
  `null` until persisted; `emails`/`phoneNumbers` are normalized in the compact
  constructor to non-null unmodifiable lists, so no layer needs null checks.
  `withId(...)` returns a copy with the id set.
- **`web/ContactController`** — REST endpoints. Accepts `ContactRequest` (a
  separate validated DTO, *never* the domain `Contact`) so clients can never
  supply an id. `create` returns 201 with a `Location` header.
- **`service/ContactService`** — business rules. **The server owns ids**:
  `create` assigns a fresh `UUID`; `update` always forces the id from the path.
  Throws `ContactNotFoundException` for missing contacts.
- **`repository/ContactRepository`** — the storage seam (the key extension
  point). The whole point of this interface is to let a future database/cloud
  implementation drop in without touching service or web code.
- **`repository/file/FileContactRepository`** — the only implementation. Holds
  all contacts in an in-memory `LinkedHashMap` (insertion-ordered), loaded from
  the JSON file at startup (`@PostConstruct`) and flushed to disk on every write.
  All methods are `synchronized` so concurrent requests can't corrupt the file.
- **`web/GlobalExceptionHandler`** — maps exceptions to RFC 7807 `ProblemDetail`
  responses: `ContactNotFoundException` → 404, validation failure → 400 with a
  per-field `errors` map.
- **`config/`** — `StorageProperties` binds `contactbook.storage.*` (with
  defaults of `type=file`, `file=./data/contacts.json`); `WebConfig` enables CORS
  for `/api/**` from `cors.allowed-origins`.

### Things worth knowing before editing

- **Adding a storage backend**: implement `ContactRepository` and make it the
  active bean. `StorageProperties.type` exists for selecting between
  implementations but is not yet wired to anything — there's only one bean today.
- **Jackson is v3** (`tools.jackson.*` package, not `com.fasterxml.jackson.*`).
  This comes with Spring Boot 4; don't add `com.fasterxml` Jackson imports.
- **Validation lives only on `ContactRequest`** (`@NotBlank`, `@Email`). The
  domain record is intentionally not annotated.
- **Tests** (`ContactControllerTest`) are plain unit tests — the controller is
  instantiated directly with a mocked service, no Spring context. Routing, JSON
  (de)serialization, `@Valid`, and the exception-handler status mapping are
  therefore *not* covered by them.

## Configuration

`src/main/resources/application.yml` — port (8080), storage type/path, CORS
allowed origins (Vite dev server at `:5173` and `:3000`). The `data/` directory
holding `contacts.json` is gitignored runtime state.