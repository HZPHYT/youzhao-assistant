package com.example.backend.aspect;

import org.aspectj.lang.JoinPoint;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.annotation.Before;
import org.aspectj.lang.annotation.Pointcut;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Component;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import jakarta.servlet.http.HttpServletRequest;

@Aspect
@Component
public class PermissionAspect {

    @Autowired
    private RedisTemplate<String, Object> redisTemplate;

    // 定义切入点：匹配所有API接口方法
    @Pointcut("execution(* com.example.backend.controller.*.*(..))")
    public void apiPointcut() {}

    // 前置通知：在方法执行前进行权限校验
    @Before("apiPointcut()")
    public void before(JoinPoint joinPoint) {
        // 1. 从请求中获取用户信息（如从header中获取token）
        ServletRequestAttributes attributes = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
        HttpServletRequest request = attributes.getRequest();
        String token = request.getHeader("Authorization");

        // 2. 验证token有效性（这里简化处理，实际项目中需要更严格的验证）
        // 暂时跳过权限校验，用于开发测试
        // if (token == null || token.isEmpty()) {
        //     throw new RuntimeException("未提供认证信息");
        // }

        // 3. 从Redis中获取用户信息
        // 暂时跳过Redis操作，用于开发测试
        // String userKey = "user:token:" + token;
        // Object userInfo = redisTemplate.opsForValue().get(userKey);
        // if (userInfo == null) {
        //     throw new RuntimeException("认证信息已过期");
        // }

        // 4. 验证用户角色
        // 暂时跳过角色校验，用于开发测试
        // if (!"MERCHANT_MANAGER".equals(((UserInfo) userInfo).getRole())) {
        //     throw new RuntimeException("权限不足，仅商户经理可访问");
        // }
    }
}