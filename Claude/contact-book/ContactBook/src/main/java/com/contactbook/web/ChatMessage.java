package com.contactbook.web;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

/** A single turn in a conversation: either a user or assistant message. */
public record ChatMessage(
    @NotBlank @Pattern(regexp = "user|assistant") String role, @NotBlank String content) {}
