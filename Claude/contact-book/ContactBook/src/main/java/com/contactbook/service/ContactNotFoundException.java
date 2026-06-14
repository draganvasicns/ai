package com.contactbook.service;

/** Thrown when an operation references a contact id that does not exist. */
public class ContactNotFoundException extends RuntimeException {
    public ContactNotFoundException(String id) {
        super("Contact not found: " + id);
    }
}
