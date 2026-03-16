package com.example.backend.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.text.PDFTextStripper;
import org.apache.poi.xwpf.extractor.XWPFWordExtractor;
import org.apache.poi.xwpf.usermodel.XWPFDocument;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.BufferedReader;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Service
public class KnowledgeServiceImpl implements KnowledgeService {

    private static final String PYTHON_API_URL = "http://localhost:8000/api/knowledge";

    @Override
    public void uploadKnowledge(MultipartFile file) throws Exception {
        // 读取文件内容
        StringBuilder content = new StringBuilder();
        String fileName = file.getOriginalFilename();
        
        if (fileName != null && fileName.endsWith(".docx")) {
            // 处理Word文档
            try (InputStream is = file.getInputStream()) {
                // 处理docx文件
                XWPFDocument document = new XWPFDocument(is);
                XWPFWordExtractor extractor = new XWPFWordExtractor(document);
                content.append(extractor.getText());
                extractor.close();
            }
        } else if (fileName != null && (fileName.endsWith(".txt") || fileName.endsWith(".md"))) {
            // 处理文本文件
            try (BufferedReader reader = new BufferedReader(
                    new InputStreamReader(file.getInputStream(), StandardCharsets.UTF_8))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    content.append(line).append("\n");
                }
            }
        } else if (fileName != null && fileName.endsWith(".pdf")) {
            // 处理PDF文件
            try (InputStream is = file.getInputStream()) {
                PDDocument document = PDDocument.load(is);
                PDFTextStripper stripper = new PDFTextStripper();
                stripper.setSortByPosition(true);
                String text = stripper.getText(document);
                content.append(text);
                document.close();
            }
        } else {
            // 不支持的文件格式
            throw new Exception("不支持的文件格式，请上传 .txt, .md, .docx 或 .pdf 文件");
        }

        // 调用Python API上传知识（使用Multipart形式）
        String boundary = UUID.randomUUID().toString();
        URL url = new URL(PYTHON_API_URL + "/upload");
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("POST");
        conn.setDoOutput(true);
        conn.setRequestProperty("Content-Type", "multipart/form-data; boundary=" + boundary);

        StringBuilder sb = new StringBuilder();
        sb.append("--").append(boundary).append("\r\n");
        sb.append("Content-Disposition: form-data; name=\"file\"; filename=\"").append(fileName).append("\"\r\n");
        sb.append("Content-Type: text/plain\r\n\r\n");
        
        byte[] contentBytes = content.toString().getBytes(StandardCharsets.UTF_8);
        byte[] headerBytes = sb.toString().getBytes(StandardCharsets.UTF_8);
        byte[] endBytes = ("\r\n--" + boundary + "--\r\n").getBytes(StandardCharsets.UTF_8);
        
        try (OutputStream os = conn.getOutputStream()) {
            os.write(headerBytes);
            os.write(contentBytes);
            os.write(endBytes);
        }

        // 读取响应
        int responseCode = conn.getResponseCode();
        if (responseCode == HttpURLConnection.HTTP_OK) {
            try (var br = new BufferedReader(
                    new InputStreamReader(conn.getInputStream(), StandardCharsets.UTF_8))) {
                StringBuilder response = new StringBuilder();
                String responseLine;
                while ((responseLine = br.readLine()) != null) {
                    response.append(responseLine.trim());
                }
            }
        } else {
            // 读取错误响应
            try (var br = new BufferedReader(
                    new InputStreamReader(conn.getErrorStream(), StandardCharsets.UTF_8))) {
                StringBuilder errorResponse = new StringBuilder();
                String responseLine;
                while ((responseLine = br.readLine()) != null) {
                    errorResponse.append(responseLine.trim());
                }
                throw new Exception("Python API 错误: " + errorResponse.toString());
            }
        }

        conn.disconnect();
    }

    @Override
    public List<Map<String, Object>> getKnowledgeList() throws Exception {
        // 调用Python API获取知识列表
        URL url = new URL(PYTHON_API_URL + "/list");
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("GET");

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
        ObjectMapper objectMapper = new ObjectMapper();
        return objectMapper.readValue(response.toString(), List.class);
    }

    @Override
    public void deleteKnowledge(String id) throws Exception {
        // 调用Python API删除知识
        URL url = new URL(PYTHON_API_URL + "/delete");
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("POST");
        conn.setRequestProperty("Content-Type", "application/json");
        conn.setDoOutput(true);

        String jsonInputString = "{\"id\": \"" + id + "\"}";
        try (var os = conn.getOutputStream()) {
            byte[] input = jsonInputString.getBytes(StandardCharsets.UTF_8);
            os.write(input, 0, input.length);
        }

        // 读取响应
        try (var br = new BufferedReader(
                new InputStreamReader(conn.getInputStream(), StandardCharsets.UTF_8))) {
            StringBuilder response = new StringBuilder();
            String responseLine;
            while ((responseLine = br.readLine()) != null) {
                response.append(responseLine.trim());
            }
        }

        conn.disconnect();
    }

    @Override
    public void clearKnowledge() throws Exception {
        // 调用Python API清空知识库
        URL url = new URL(PYTHON_API_URL + "/clear");
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("POST");

        // 读取响应
        try (var br = new BufferedReader(
                new InputStreamReader(conn.getInputStream(), StandardCharsets.UTF_8))) {
            StringBuilder response = new StringBuilder();
            String responseLine;
            while ((responseLine = br.readLine()) != null) {
                response.append(responseLine.trim());
            }
        }

        conn.disconnect();
    }
}
