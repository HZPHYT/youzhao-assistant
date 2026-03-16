from app.models import init_db, SessionLocal, CustomerCredit, CustomerApproval

def seed_data():
    init_db()
    db = SessionLocal()
    
    try:
        credit_data = [
            CustomerCredit(customer_id="C001", customer_name="张三", credit_limit=500000, loan_limit=300000, 
                          used_credit=120000, used_loan=80000, credit_status="正常", loan_status="正常", update_time="2024-01-15"),
            CustomerCredit(customer_id="C002", customer_name="李四", credit_limit=800000, loan_limit=500000,
                          used_credit=350000, used_loan=200000, credit_status="正常", loan_status="正常", update_time="2024-01-14"),
            CustomerCredit(customer_id="C003", customer_name="王五", credit_limit=300000, loan_limit=150000,
                          used_credit=50000, used_loan=30000, credit_status="正常", loan_status="正常", update_time="2024-01-13"),
            CustomerCredit(customer_id="C004", customer_name="赵六", credit_limit=1000000, loan_limit=800000,
                          used_credit=600000, used_loan=450000, credit_status="正常", loan_status="逾期", update_time="2024-01-12"),
            CustomerCredit(customer_id="C005", customer_name="钱七", credit_limit=600000, loan_limit=400000,
                          used_credit=180000, used_loan=120000, credit_status="正常", loan_status="正常", update_time="2024-01-11"),
            CustomerCredit(customer_id="C006", customer_name="孙八", credit_limit=450000, loan_limit=250000,
                          used_credit=100000, used_loan=60000, credit_status="冻结", loan_status="正常", update_time="2024-01-10"),
            CustomerCredit(customer_id="C007", customer_name="周九", credit_limit=700000, loan_limit=450000,
                          used_credit=220000, used_loan=150000, credit_status="正常", loan_status="正常", update_time="2024-01-09"),
            CustomerCredit(customer_id="C008", customer_name="吴十", credit_limit=900000, loan_limit=600000,
                          used_credit=400000, used_loan=280000, credit_status="正常", loan_status="正常", update_time="2024-01-08"),
            CustomerCredit(customer_id="C009", customer_name="郑一", credit_limit=550000, loan_limit=350000,
                          used_credit=160000, used_loan=90000, credit_status="正常", loan_status="正常", update_time="2024-01-07"),
            CustomerCredit(customer_id="C010", customer_name="陈二", credit_limit=650000, loan_limit=420000,
                          used_credit=200000, used_loan=110000, credit_status="正常", loan_status="正常", update_time="2024-01-06"),
        ]
        
        approval_data = [
            CustomerApproval(customer_id="C001", customer_name="张三", apply_type="贷款申请", apply_amount=200000,
                          apply_date="2024-01-10", approval_status="已通过", approval_result="批准贷款20万元", approver="王经理", approval_date="2024-01-12", remark="资质良好"),
            CustomerApproval(customer_id="C002", customer_name="李四", apply_type="额度提升", apply_amount=300000,
                          apply_date="2024-01-08", approval_status="已通过", approval_result="提升额度30万元", approver="李经理", approval_date="2024-01-10", remark="还款记录良好"),
            CustomerApproval(customer_id="C003", customer_name="王五", apply_type="贷款申请", apply_amount=100000,
                          apply_date="2024-01-12", approval_status="审批中", approval_result="待审批", remark="材料齐全"),
            CustomerApproval(customer_id="C004", customer_name="赵六", apply_type="贷款申请", apply_amount=500000,
                          apply_date="2024-01-05", approval_status="已拒绝", approval_result="负债率过高", approver="张经理", approval_date="2024-01-07", remark="风险较高"),
            CustomerApproval(customer_id="C005", customer_name="钱七", apply_type="额度提升", apply_amount=200000,
                          apply_date="2024-01-11", approval_status="已通过", approval_result="提升额度20万元", approver="陈经理", approval_date="2024-01-13", remark="综合评分优秀"),
            CustomerApproval(customer_id="C006", customer_name="孙八", apply_type="贷款申请", apply_amount=150000,
                          apply_date="2024-01-14", approval_status="审批中", approval_result="待审批", remark="需补充收入证明"),
            CustomerApproval(customer_id="C007", customer_name="周九", apply_type="额度提升", apply_amount=250000,
                          apply_date="2024-01-09", approval_status="已通过", approval_result="提升额度25万元", approver="刘经理", approval_date="2024-01-11", remark="经营状况良好"),
            CustomerApproval(customer_id="C008", customer_name="吴十", apply_type="贷款申请", apply_amount=400000,
                          apply_date="2024-01-07", approval_status="已通过", approval_result="批准贷款40万元", approver="王经理", approval_date="2024-01-09", remark="抵押物充足"),
            CustomerApproval(customer_id="C009", customer_name="郑一", apply_type="贷款申请", apply_amount=200000,
                          apply_date="2024-01-13", approval_status="审批中", approval_result="待审批", remark="等风控审核"),
            CustomerApproval(customer_id="C010", customer_name="陈二", apply_type="额度提升", apply_amount=180000,
                          apply_date="2024-01-06", approval_status="已通过", approval_result="提升额度18万元", approver="李经理", approval_date="2024-01-08", remark="历史还款正常"),
        ]
        
        for c in credit_data:
            db.merge(c)
        for a in approval_data:
            db.merge(a)
        
        db.commit()
        print(f"数据初始化成功")
        print(f"已插入 {len(credit_data)} 条客户额度数据")
        print(f"已插入 {len(approval_data)} 条客户审批数据")
        
    except Exception as e:
        db.rollback()
        print(f"数据初始化失败: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
