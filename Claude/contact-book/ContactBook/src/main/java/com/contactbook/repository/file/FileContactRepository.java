package com.contactbook.repository.file;

import com.contactbook.config.StorageProperties;
import com.contactbook.domain.Contact;
import com.contactbook.repository.ContactRepository;
import org.springframework.stereotype.Repository;

import jakarta.annotation.PostConstruct;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.ObjectMapper;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * {@link ContactRepository} implementation that persists contacts to a JSON file.
 *
 * <p>Contacts are held in memory (keyed by id, insertion-ordered) and flushed to
 * the configured file on every write. Access is synchronised so concurrent web
 * requests cannot corrupt the file or the in-memory map. This is the default
 * storage for {@code contactbook.storage.type=file}.</p>
 */
@Repository
public class FileContactRepository implements ContactRepository {

    private final Path file;
    private final ObjectMapper objectMapper;
    private final Map<String, Contact> contacts = new LinkedHashMap<>();

    public FileContactRepository(StorageProperties properties, ObjectMapper objectMapper) {
        this.file = Path.of(properties.file());
        this.objectMapper = objectMapper;
    }

    @PostConstruct
    void load() {
        if (!Files.exists(file)) {
            return;
        }
        try {
            List<Contact> stored = objectMapper.readValue(
                    Files.readAllBytes(file), new TypeReference<List<Contact>>() {});
            for (Contact contact : stored) {
                contacts.put(contact.id(), contact);
            }
        } catch (IOException e) {
            throw new UncheckedIOException("Failed to read contacts from " + file, e);
        }
    }

    @Override
    public synchronized List<Contact> findAll() {
        return new ArrayList<>(contacts.values());
    }

    @Override
    public synchronized Optional<Contact> findById(String id) {
        return Optional.ofNullable(contacts.get(id));
    }

    @Override
    public synchronized Contact save(Contact contact) {
        contacts.put(contact.id(), contact);
        flush();
        return contact;
    }

    @Override
    public synchronized boolean deleteById(String id) {
        boolean removed = contacts.remove(id) != null;
        if (removed) {
            flush();
        }
        return removed;
    }

    private void flush() {
        try {
            if (file.getParent() != null) {
                Files.createDirectories(file.getParent());
            }
            objectMapper.writerWithDefaultPrettyPrinter()
                    .writeValue(file.toFile(), new ArrayList<>(contacts.values()));
        } catch (IOException e) {
            throw new UncheckedIOException("Failed to write contacts to " + file, e);
        }
    }
}