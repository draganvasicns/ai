package com.contactbook.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * Binds the {@code contactbook.storage.*} configuration keys.
 *
 * @param type which storage implementation to activate (e.g. {@code file}).
 *             Reserved for future use when more than one implementation exists.
 * @param file path to the JSON file used by the file-based storage.
 */
@ConfigurationProperties(prefix = "contactbook.storage")
public record StorageProperties(
        String type,
        String file
) {
    public StorageProperties {
        if (type == null || type.isBlank()) {
            type = "file";
        }
        if (file == null || file.isBlank()) {
            file = "./data/contacts.json";
        }
    }
}
