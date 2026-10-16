package com.example.web;

import com.example.service.UserService;
import org.springframework.stereotype.Component;
import org.springframework.web.bind.annotation.RestController;

@Component
@RestController
public class UserController {
    private final UserService service;
}
