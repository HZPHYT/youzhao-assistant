package com.example.backend.controller;

import com.example.backend.service.RagEvaluationService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/rag")
@CrossOrigin(origins = "*")
public class RagEvaluationController {

    @Autowired
    private RagEvaluationService ragEvaluationService;

    @PostMapping("/evaluate")
    public ResponseEntity<Map<String, Object>> evaluateRag(@RequestBody Map<String, Object> request) {
        try {
            Map<String, Object> results = ragEvaluationService.evaluateRag(request);
            return ResponseEntity.ok(results);
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(Map.of("error", "评测失败: " + e.getMessage()));
        }
    }
}
