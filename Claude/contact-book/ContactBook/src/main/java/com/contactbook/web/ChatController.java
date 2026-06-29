package com.contactbook.web;

import com.contactbook.service.ChatService;
import jakarta.validation.Valid;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Chat endpoint that proxies the full conversation history to Claude and returns the reply.
 *
 * <pre>
 *   POST /api/chat   send the conversation history, get Claude's reply
 * </pre>
 */
@RestController
@RequestMapping("/api/chat")
public class ChatController {

  private static final Logger log = LoggerFactory.getLogger(ChatController.class);

  private final ChatService service;

  public ChatController(ChatService service) {
    this.service = service;
  }

  @PostMapping
  public ChatResponse chat(@Valid @RequestBody ChatRequest request) {
    log.info("POST /api/chat - {} messages", request.messages().size());
    return new ChatResponse(service.chat(request.messages()));
  }
}
