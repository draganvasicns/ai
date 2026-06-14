package com.contactbook.web;

import com.contactbook.domain.Contact;
import com.contactbook.service.ContactService;
import jakarta.validation.Valid;
import java.net.URI;
import java.util.List;
import org.springframework.http.HttpStatus;
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
public class ContactController {

  private final ContactService service;

  public ContactController(ContactService service) {
    this.service = service;
  }

  @GetMapping
  public List<Contact> list() {
    return service.findAll();
  }

  @GetMapping("/{id}")
  public Contact get(@PathVariable String id) {
    return service.findById(id);
  }

  @PostMapping
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
  public Contact update(@PathVariable String id, @Valid @RequestBody ContactRequest request) {
    return service.update(id, request.toContact());
  }

  @DeleteMapping("/{id}")
  @ResponseStatus(HttpStatus.NO_CONTENT)
  public void delete(@PathVariable String id) {
    service.delete(id);
  }
}
