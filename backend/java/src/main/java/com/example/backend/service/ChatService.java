package com.example.backend.service;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;

@Service
public class ChatService {

    @Autowired
    private RedisTemplate<String, Object> redisTemplate;

    private final RestTemplate restTemplate = new RestTemplate();
    private final String pythonServiceUrl = "http://localhost:8000/api/chat";

    public Map<String, Object> handleChat(String message) {
        String cacheKey = "chat:cache:" + message.hashCode();
        
        try {
            if (redisTemplate.hasKey(cacheKey)) {
                String cachedAnswer = (String) redisTemplate.opsForValue().get(cacheKey);
                Map<String, Object> response = new HashMap<>();
                response.put("answer", cachedAnswer);
                return response;
            }
        } catch (Exception e) {
            // Redis不可用，继续执行
        }

        Map<String, String> requestBody = new HashMap<>();
        requestBody.put("message", message);

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        HttpEntity<Map<String, String>> entity = new HttpEntity<>(requestBody, headers);

        ResponseEntity<Map> responseEntity = restTemplate.postForEntity(pythonServiceUrl, entity, Map.class);
        Map<String, Object> response = responseEntity.getBody();

        try {
            if (response != null && response.containsKey("answer")) {
                redisTemplate.opsForValue().set(cacheKey, response.get("answer"), 1, TimeUnit.HOURS);
            }
        } catch (Exception e) {
            // Redis不可用，忽略缓存
        }

        return response;
    }
}