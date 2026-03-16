-- 创建数据库
CREATE DATABASE IF NOT EXISTS youzhao;

-- 使用数据库
USE youzhao;

-- 创建客户表
CREATE TABLE IF NOT EXISTS customer (
    id INT PRIMARY KEY AUTO_INCREMENT,
    customer_id VARCHAR(50) NOT NULL,
    name VARCHAR(100) NOT NULL,
    qualification_level VARCHAR(50),
    credit_limit DECIMAL(18, 2),
    marketing_history TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 创建产品表
CREATE TABLE IF NOT EXISTS product (
    id INT PRIMARY KEY AUTO_INCREMENT,
    product_id VARCHAR(50) NOT NULL,
    name VARCHAR(100) NOT NULL,
    interest_rate DECIMAL(5, 2),
    installment_options TEXT,
    discount_policy TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 创建审批表
CREATE TABLE IF NOT EXISTS approval (
    id INT PRIMARY KEY AUTO_INCREMENT,
    approval_id VARCHAR(50) NOT NULL,
    customer_id VARCHAR(50) NOT NULL,
    status VARCHAR(50),
    progress VARCHAR(100),
    failure_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 创建营销资源表
CREATE TABLE IF NOT EXISTS marketing_resource (
    id INT PRIMARY KEY AUTO_INCREMENT,
    resource_id VARCHAR(50) NOT NULL,
    type VARCHAR(50),
    applicable_scenario TEXT,
    content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 插入示例数据
-- 客户表
INSERT INTO customer (customer_id, name, qualification_level, credit_limit, marketing_history) VALUES
('C001', '张三', 'A', 100000.00, '曾购买过我们的理财产品，对我们的服务满意度高'),
('C002', '李四', 'B', 50000.00, '首次接触我们的服务，对贷款产品有兴趣'),
('C003', '王五', 'A', 150000.00, '长期合作客户，信用记录良好');

-- 产品表
INSERT INTO product (product_id, name, interest_rate, installment_options, discount_policy) VALUES
('P001', '个人消费贷款', 4.5, '3期、6期、12期', '新客户首贷享受利率9折优惠'),
('P002', '经营周转贷款', 5.2, '6期、12期、24期', '老客户享受利率8.5折优惠'),
('P003', '购车贷款', 3.8, '12期、24期、36期', '指定车型享受利率8折优惠');

-- 审批表
INSERT INTO approval (approval_id, customer_id, status, progress, failure_reason) VALUES
('A001', 'C001', '已通过', '已完成', NULL),
('A002', 'C002', '审批中', '资料审核中', NULL),
('A003', 'C003', '已拒绝', '审批完成', '信用记录不良');

-- 营销资源表
INSERT INTO marketing_resource (resource_id, type, applicable_scenario, content) VALUES
('M001', '优惠券', '新客户首贷', '首贷客户可获得500元优惠券'),
('M002', '活动', '节日促销', '国庆节期间贷款可享受利率优惠'),
('M003', '礼品', '老客户推荐', '推荐新客户成功贷款可获得精美礼品');
