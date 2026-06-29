package com.contactbook.config;

import java.util.List;
import org.springframework.boot.context.properties.ConfigurationProperties;

/** Binds the {@code cors.*} configuration keys. */
@ConfigurationProperties(prefix = "cors")
public record CorsProperties(List<String> allowedOrigins) {}
