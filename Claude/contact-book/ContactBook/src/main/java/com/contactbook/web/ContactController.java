package com.contactbook.web;

import com.contactbook.domain.Contact;
import com.contactbook.service.ContactService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import java.net.URI;
import java.util.List;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.support.ServletUriComponentsBuilder;

/**
 * REST API for managing contacts.
 *
 * <pre>
 *   GET    /api/contacts        list all contacts
 *   GET    /api/contacts/{id}   fetch one contact
 *   POST   /api/contacts        create a contact (server assigns the id)
 *   PUT    /api/contacts/{id}   replace an existing contact
 *   DELETE /api/contacts/{id}   delete a contact
 * </pre>
 *
 * <p>Request bodies are validated ({@link ContactRequest}); a missing contact yields 404 and a
 * validation failure yields 400 (see {@code com.contactbook.web.GlobalExceptionHandler}).
 */
@RestController
@RequestMapping("/api/contacts")
@Tag(name = "Contacts", description = "CRUD operations on contacts")
public class ContactController {

  private static final Logger log = LoggerFactory.getLogger(ContactController.class);

  private final ContactService service;

  public ContactController(ContactService service) {
    this.service = service;
  }

  @GetMapping
  @Operation(summary = "List all contacts")
  public List<Contact> list() {
    log.info("GET /api/contacts");
    return service.findAll();
  }

  @GetMapping("/{id}")
  @Operation(summary = "Get a contact by id")
  @ApiResponse(
      responseCode = "200",
      description = "Contact found",
      content = @Content(schema = @Schema(implementation = Contact.class)))
  @ApiResponse(
      responseCode = "404",
      description = "Contact not found",
      content = @Content(schema = @Schema(implementation = ProblemDetail.class)))
  public Contact get(@PathVariable String id) {
    log.info("GET /api/contacts/{}", id);
    return service.findById(id);
  }

  @PostMapping
  @Operation(summary = "Create a new contact (server assigns the id)")
  @ApiResponse(
      responseCode = "201",
      description = "Created; the Location header holds the URI of the new contact",
      content = @Content(schema = @Schema(implementation = Contact.class)))
  @ApiResponse(
      responseCode = "400",
      description = "Validation failed",
      content = @Content(schema = @Schema(implementation = ProblemDetail.class)))
  public ResponseEntity<Contact> create(@Valid @RequestBody ContactRequest request) {
    log.info("POST /api/contacts - {} {}", request.firstName(), request.lastName());
    Contact created = service.create(request.toContact());
    URI location =
        ServletUriComponentsBuilder.fromCurrentRequest()
            .path("/{id}")
            .buildAndExpand(created.id())
            .toUri();
    return ResponseEntity.created(location).body(created);
  }

  @PutMapping("/{id}")
  @Operation(summary = "Replace an existing contact")
  @ApiResponse(
      responseCode = "200",
      description = "Contact updated",
      content = @Content(schema = @Schema(implementation = Contact.class)))
  @ApiResponse(
      responseCode = "400",
      description = "Validation failed",
      content = @Content(schema = @Schema(implementation = ProblemDetail.class)))
  @ApiResponse(
      responseCode = "404",
      description = "Contact not found",
      content = @Content(schema = @Schema(implementation = ProblemDetail.class)))
  public Contact update(@PathVariable String id, @Valid @RequestBody ContactRequest request) {
    log.info("PUT /api/contacts/{} - {} {}", id, request.firstName(), request.lastName());
    return service.update(id, request.toContact());
  }

  @DeleteMapping("/{id}")
  @ResponseStatus(HttpStatus.NO_CONTENT)
  @Operation(summary = "Delete a contact")
  @ApiResponse(responseCode = "204", description = "Deleted")
  @ApiResponse(
      responseCode = "404",
      description = "Contact not found",
      content = @Content(schema = @Schema(implementation = ProblemDetail.class)))
  public void delete(@PathVariable String id) {
    log.info("DELETE /api/contacts/{}", id);
    service.delete(id);
  }
}
