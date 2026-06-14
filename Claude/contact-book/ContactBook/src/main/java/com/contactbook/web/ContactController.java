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
@Tag(name = "Contacts", description = "CRUD operacije nad kontaktima")
public class ContactController {

  private final ContactService service;

  public ContactController(ContactService service) {
    this.service = service;
  }

  @GetMapping
  @Operation(summary = "Lista svih kontakata")
  public List<Contact> list() {
    return service.findAll();
  }

  @GetMapping("/{id}")
  @Operation(summary = "Vrati kontakt po id-u")
  @ApiResponse(
      responseCode = "200",
      description = "Kontakt pronađen",
      content = @Content(schema = @Schema(implementation = Contact.class)))
  @ApiResponse(
      responseCode = "404",
      description = "Kontakt ne postoji",
      content = @Content(schema = @Schema(implementation = ProblemDetail.class)))
  public Contact get(@PathVariable String id) {
    return service.findById(id);
  }

  @PostMapping
  @Operation(summary = "Kreiraj novi kontakt (server dodeljuje id)")
  @ApiResponse(
      responseCode = "201",
      description = "Kreiran; Location header sadrži URI novog kontakta",
      content = @Content(schema = @Schema(implementation = Contact.class)))
  @ApiResponse(
      responseCode = "400",
      description = "Validacija nije prošla",
      content = @Content(schema = @Schema(implementation = ProblemDetail.class)))
  public ResponseEntity<Contact> create(@Valid @RequestBody ContactRequest request) {
    Contact created = service.create(request.toContact());
    URI location =
        ServletUriComponentsBuilder.fromCurrentRequest()
            .path("/{id}")
            .buildAndExpand(created.id())
            .toUri();
    return ResponseEntity.created(location).body(created);
  }

  @PutMapping("/{id}")
  @Operation(summary = "Zameni postojeći kontakt")
  @ApiResponse(
      responseCode = "200",
      description = "Kontakt izmenjen",
      content = @Content(schema = @Schema(implementation = Contact.class)))
  @ApiResponse(
      responseCode = "400",
      description = "Validacija nije prošla",
      content = @Content(schema = @Schema(implementation = ProblemDetail.class)))
  @ApiResponse(
      responseCode = "404",
      description = "Kontakt ne postoji",
      content = @Content(schema = @Schema(implementation = ProblemDetail.class)))
  public Contact update(@PathVariable String id, @Valid @RequestBody ContactRequest request) {
    return service.update(id, request.toContact());
  }

  @DeleteMapping("/{id}")
  @ResponseStatus(HttpStatus.NO_CONTENT)
  @Operation(summary = "Obriši kontakt")
  @ApiResponse(responseCode = "204", description = "Obrisan")
  @ApiResponse(
      responseCode = "404",
      description = "Kontakt ne postoji",
      content = @Content(schema = @Schema(implementation = ProblemDetail.class)))
  public void delete(@PathVariable String id) {
    service.delete(id);
  }
}
