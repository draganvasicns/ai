package com.contactbook.web;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotEmpty;
import java.util.List;

/** Request body for POST /api/chat. Carries the full conversation history. */
public record ChatRequest(@NotEmpty List<@Valid ChatMessage> messages) {}
