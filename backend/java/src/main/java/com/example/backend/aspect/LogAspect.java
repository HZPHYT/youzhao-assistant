package com.example.backend.aspect;

import org.aspectj.lang.JoinPoint;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import jakarta.servlet.http.HttpServletRequest;

@Aspect
@Component
public class LogAspect {

    private static final Logger logger = LoggerFactory.getLogger(LogAspect.class);

    @Pointcut("execution(* com.example.backend.controller.*.*(..))")
    public void controllerPointcut() {}

    @Around("controllerPointcut()")
    public Object around(ProceedingJoinPoint joinPoint) throws Throwable {
        long startTime = System.currentTimeMillis();
        
        ServletRequestAttributes attributes = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
        HttpServletRequest request = attributes.getRequest();
        
        String className = joinPoint.getTarget().getClass().getSimpleName();
        String methodName = joinPoint.getSignature().getName();
        String httpMethod = request.getMethod();
        String requestUri = request.getRequestURI();
        
        logger.info("=== 请求开始 ===");
        logger.info("URL: {} {}", httpMethod, requestUri);
        logger.info("Controller: {}.{}", className, methodName);
        
        Object result = joinPoint.proceed();
        
        long costTime = System.currentTimeMillis() - startTime;
        logger.info("=== 请求结束 ===");
        logger.info("耗时: {}ms", costTime);
        
        return result;
    }

    @AfterThrowing(pointcut = "controllerPointcut()", throwing = "exception")
    public void afterThrowing(JoinPoint joinPoint, Exception exception) {
        logger.error("=== 请求异常 ===");
        logger.error("异常信息: {}", exception.getMessage());
        logger.error("异常方法: {}.{}", 
            joinPoint.getTarget().getClass().getSimpleName(),
            joinPoint.getSignature().getName());
    }
}
