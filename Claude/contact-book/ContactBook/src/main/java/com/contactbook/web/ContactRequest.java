package com.contactbook.web;

import com.contactbook.domain.Contact;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;

import java.util.List;

/**
 * Payload accepted by create/update endpoints. Validated by Bean Validation
 * before it reaches the service layer. The id is never accepted from the client;
 * it is owned by the server.
 */
public record ContactRequest(
        @NotBlank(message = "firstName is required")
        String firstName,

        @NotBlank(message = "lastName is required")
        String lastName,

        List<@Email(message = "must be a valid email address") String> emails,

        List<String> phoneNumbers
) {
    /** Maps this request to a domain object (without an id). */
    public Contact toContact() {
        return new Contact(null, firstName, lastName, emails, phoneNumbers);
    }
}
