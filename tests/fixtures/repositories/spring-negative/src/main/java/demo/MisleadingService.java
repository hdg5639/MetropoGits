package demo;

import demo.annotations.Service;

@Service
public class MisleadingService {
    private String example = "@org.springframework.stereotype.Service";
}
