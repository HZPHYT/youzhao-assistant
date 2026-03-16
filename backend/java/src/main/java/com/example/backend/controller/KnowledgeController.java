package com.example.backend.controller;

import com.example.backend.service.KnowledgeService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/knowledge")
@CrossOrigin(origins = "*")
public class KnowledgeController {

    @Autowired
    private KnowledgeService knowledgeService;

    @PostMapping("/upload")
    public ResponseEntity<Map<String, String>> uploadKnowledge(@RequestParam("file") MultipartFile file) {
        try {
            knowledgeService.uploadKnowledge(file);
            return ResponseEntity.ok(Map.of("message", "知识上传成功"));
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(Map.of("message", "上传失败: " + e.getMessage()));
        }
    }

    @GetMapping("/list")
    public ResponseEntity<List<Map<String, Object>>> getKnowledgeList() {
        try {
            List<Map<String, Object>> knowledgeList = knowledgeService.getKnowledgeList();
            return ResponseEntity.ok(knowledgeList);
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(null);
        }
    }

    @DeleteMapping("/delete")
    public ResponseEntity<Map<String, String>> deleteKnowledge(@RequestBody Map<String, String> request) {
        try {
            String id = request.get("id");
            knowledgeService.deleteKnowledge(id);
            return ResponseEntity.ok(Map.of("message", "删除成功"));
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(Map.of("message", "删除失败: " + e.getMessage()));
        }
    }

    @PostMapping("/clear")
    public ResponseEntity<Map<String, String>> clearKnowledge() {
        try {
            knowledgeService.clearKnowledge();
            return ResponseEntity.ok(Map.of("message", "知识库已清空"));
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(Map.of("message", "清空失败: " + e.getMessage()));
        }
    }
}
