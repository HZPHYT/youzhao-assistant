package com.example.backend.service;

import org.springframework.stereotype.Service;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.Map;

@Service
public class RagEvaluationServiceImpl implements RagEvaluationService {

    private static final String PYTHON_API_URL = "http://localhost:8000/api/rag/evaluate";

    @Override
    public Map<String, Object> evaluateRag(Map<String, Object> request) throws Exception {
        // 调用Python API进行RAG评测
        URL url = new URL(PYTHON_API_URL);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("POST");
        conn.setRequestProperty("Content-Type", "application/json");
        conn.setDoOutput(true);

        // 构建JSON请求体
        StringBuilder jsonBuilder = new StringBuilder();
        jsonBuilder.append("{");
        jsonBuilder.append("\"questionCount\": " + request.get("questionCount") + ",");
        jsonBuilder.append("\"evaluationType\": \"" + request.get("evaluationType") + "\"");
        jsonBuilder.append("}");

        String jsonInputString = jsonBuilder.toString();
        try (var os = conn.getOutputStream()) {
            byte[] input = jsonInputString.getBytes(StandardCharsets.UTF_8);
            os.write(input, 0, input.length);
        }

        // 读取响应
        StringBuilder response = new StringBuilder();
        try (var br = new BufferedReader(
                new InputStreamReader(conn.getInputStream(), StandardCharsets.UTF_8))) {
            String responseLine;
            while ((responseLine = br.readLine()) != null) {
                response.append(responseLine.trim());
            }
        }

        conn.disconnect();

        // 解析响应
        // 这里简化处理，实际应该使用JSON解析库
        return Map.of();
    }
}
