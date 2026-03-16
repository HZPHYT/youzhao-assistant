package com.example.backend.service;

import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.Map;

public interface KnowledgeService {
    void uploadKnowledge(MultipartFile file) throws Exception;
    List<Map<String, Object>> getKnowledgeList() throws Exception;
    void deleteKnowledge(String id) throws Exception;
    void clearKnowledge() throws Exception;
}
