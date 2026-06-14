package com.contactbook.service;

import com.contactbook.domain.Contact;
import com.contactbook.repository.ContactRepository;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Service;

/**
 * Application service for managing {@link Contact}s.
 *
 * <p>Holds the CRUD business rules and keeps the web layer free of storage concerns. The server
 * owns contact ids: {@link #create(Contact)} assigns a new id and updates always preserve the id
 * from the path.
 */
@Service
public class ContactService {

  private final ContactRepository repository;

  public ContactService(ContactRepository repository) {
    this.repository = repository;
  }

  /** Returns all contacts. */
  public List<Contact> findAll() {
    return repository.findAll();
  }

  /**
   * Returns the contact with the given id.
   *
   * @throws ContactNotFoundException if no such contact exists
   */
  public Contact findById(String id) {
    return repository.findById(id).orElseThrow(() -> new ContactNotFoundException(id));
  }

  /** Creates a new contact, assigning it a server-generated id. */
  public Contact create(Contact contact) {
    Contact toSave = contact.withId(UUID.randomUUID().toString());
    return repository.save(toSave);
  }

  /**
   * Replaces the contact identified by {@code id} with the given data.
   *
   * @throws ContactNotFoundException if no contact with that id exists
   */
  public Contact update(String id, Contact contact) {
    if (repository.findById(id).isEmpty()) {
      throw new ContactNotFoundException(id);
    }
    return repository.save(contact.withId(id));
  }

  /**
   * Deletes the contact with the given id.
   *
   * @throws ContactNotFoundException if no contact with that id exists
   */
  public void delete(String id) {
    if (!repository.deleteById(id)) {
      throw new ContactNotFoundException(id);
    }
  }
}
