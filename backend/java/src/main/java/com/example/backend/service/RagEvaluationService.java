package com.example.backend.service;

import java.util.Map;

public interface RagEvaluationService {
    Map<String, Object> evaluateRag(Map<String, Object> request) throws Exception;
}
