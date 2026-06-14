package com.contactbook.repository;

import com.contactbook.domain.Contact;
import java.util.List;
import java.util.Optional;

/**
 * Storage abstraction for {@link Contact} entities.
 *
 * <p>This interface is the seam that isolates <em>where</em> contacts are stored from the rest of
 * the application. The current implementation persists to a JSON file ({@code
 * com.contactbook.repository.file.FileContactRepository}); a future database- or cloud-backed
 * implementation can be dropped in by providing another bean of this type, without changing the
 * service or web layers.
 */
public interface ContactRepository {

  /** Returns all stored contacts. */
  List<Contact> findAll();

  /** Returns the contact with the given id, if present. */
  Optional<Contact> findById(String id);

  /**
   * Inserts or replaces the given contact (keyed by {@link Contact#id()}) and returns the persisted
   * instance.
   */
  Contact save(Contact contact);

  /**
   * Deletes the contact with the given id.
   *
   * @return {@code true} if a contact was removed, {@code false} if none existed
   */
  boolean deleteById(String id);
}
