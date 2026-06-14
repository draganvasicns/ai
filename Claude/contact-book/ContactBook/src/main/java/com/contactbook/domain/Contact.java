package com.contactbook.domain;

import java.util.List;

/**
 * A contact in the address book.
 *
 * <p>This is the core domain type shared by the web, service, and repository layers. It is an
 * immutable value: the {@code id} is owned by the server and is {@code null} for a contact that has
 * not yet been persisted (see {@code com.contactbook.web.ContactRequest#toContact()}).
 *
 * <p>The {@code emails} and {@code phoneNumbers} lists are normalised to non-null, unmodifiable
 * lists so callers never have to null-check or worry about later mutation.
 *
 * @param id server-assigned identifier, or {@code null} before persisting
 * @param firstName given name
 * @param lastName family name
 * @param emails email addresses (never {@code null})
 * @param phoneNumbers phone numbers (never {@code null})
 */
public record Contact(
    String id, String firstName, String lastName, List<String> emails, List<String> phoneNumbers) {
  public Contact {
    emails = emails == null ? List.of() : List.copyOf(emails);
    phoneNumbers = phoneNumbers == null ? List.of() : List.copyOf(phoneNumbers);
  }

  /** Returns a copy of this contact with the given id assigned. */
  public Contact withId(String id) {
    return new Contact(id, firstName, lastName, emails, phoneNumbers);
  }
}
