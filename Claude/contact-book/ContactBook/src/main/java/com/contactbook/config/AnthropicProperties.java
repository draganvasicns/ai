package com.contactbook.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

/** Binds the {@code anthropic.*} configuration keys. */
@ConfigurationProperties(prefix = "anthropic")
public record AnthropicProperties(String apiKey, String model, long maxTokens) {
  public AnthropicProperties {
    if (model == null || model.isBlank()) {
      model = "claude-sonnet-4-6";
    }
    if (maxTokens <= 0) {
      maxTokens = 1024;
    }
  }
}
