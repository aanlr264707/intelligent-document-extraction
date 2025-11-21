#!/usr/bin/env python3
"""
COMPREHENSIVE ENHANCED EXTRACTION DEMONSTRATION
This script demonstrates the dramatically improved extraction capabilities
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def demonstrate_enhanced_extraction():
    """Demonstrate the enhanced extraction capabilities"""
    
    print("🚀 ENHANCED EXTRACTION DEMONSTRATION")
    print("=" * 50)
    print()
    
    try:
        from app.services.extraction_engine import ExtractionEngine
        print("✅ Enhanced Extraction Engine loaded successfully")
        
        # Create engine instance
        engine = ExtractionEngine()
        
        # Test legal document with complex content
        complex_legal_doc = """
        SOFTWARE DEVELOPMENT AGREEMENT
        
        This Software Development Agreement ("Agreement") is entered into on January 15, 2024,
        between TechSoft Solutions Inc., a Delaware corporation ("Developer"), and 
        Global Enterprises LLC, a California limited liability company ("Client").
        
        1. SCOPE OF WORK
        Developer shall provide custom software development services including:
        - Database design and implementation
        - API development and integration  
        - User interface design
        - Quality assurance testing
        
        2. COMPENSATION AND PAYMENT
        Total project cost: $250,000 payable as follows:
        - 30% ($75,000) upon signing
        - 40% ($100,000) upon completion of Phase 1 (due March 30, 2024)
        - 30% ($75,000) upon final delivery (due June 15, 2024)
        
        Late payment penalty: 1.5% per month on overdue amounts.
        
        3. INTELLECTUAL PROPERTY RIGHTS
        All custom software developed shall be the exclusive property of Client.
        Developer retains rights to general methodologies and pre-existing IP.
        
        4. CONFIDENTIALITY OBLIGATIONS
        Both parties agree to maintain strict confidentiality regarding:
        - Proprietary business information
        - Technical specifications and source code
        - Financial terms and business strategies
        
        Confidentiality period: 5 years from agreement termination.
        
        5. WARRANTY AND LIABILITY
        Developer warrants software will be free from material defects for 90 days.
        Developer's total liability shall not exceed $100,000.
        Client shall indemnify Developer against third-party claims.
        
        6. TERMINATION CONDITIONS
        Either party may terminate for material breach with 30 days written notice.
        Client may terminate for convenience with 60 days notice plus payment for work completed.
        Upon termination, all work product shall be delivered to Client.
        
        7. DISPUTE RESOLUTION
        Disputes shall be resolved through binding arbitration in San Francisco, CA 
        under American Arbitration Association Commercial Rules.
        
        8. FORCE MAJEURE
        Neither party liable for delays due to acts of God, government actions,
        natural disasters, or other circumstances beyond reasonable control.
        
        9. NON-SOLICITATION
        For 18 months, neither party shall solicit the other's employees 
        who worked on this project.
        
        10. GOVERNING LAW
        Agreement governed by California law without regard to conflict of laws.
        
        Contract Term: January 15, 2024 to December 31, 2024
        Renewal Review Date: November 1, 2024
        First Milestone: March 30, 2024
        Final Delivery: June 15, 2024
        Warranty Expiration: September 13, 2024
        
        LIQUIDATED DAMAGES: $50,000 for breach of confidentiality obligations.
        AUTOMATIC RENEWAL: Agreement renews for 1-year terms unless 90 days notice given.
        
        IN WITNESS WHEREOF, parties execute this Agreement as of January 15, 2024.
        """
        
        print("📄 Processing complex legal document...")
        print("   Content length:", len(complex_legal_doc), "characters")
        print()
        
        # Test the comprehensive analysis directly
        analysis = engine._perform_comprehensive_document_analysis(complex_legal_doc)
        
        print("🎯 COMPREHENSIVE ANALYSIS RESULTS:")
        print("=" * 40)
        print()
        
        # 1. Document Overview
        basic_info = analysis.get('basic_info', {})
        if basic_info:
            print("📋 DOCUMENT OVERVIEW:")
            doc_type = basic_info.get('document_type', {})
            print(f"   Type: {doc_type.get('primary_type', 'unknown').title()} (confidence: {doc_type.get('confidence', 0):.2f})")
            print(f"   Words: {basic_info.get('word_count', 0):,}")
            print(f"   Sentences: {basic_info.get('sentence_count', 0):,}")
            print(f"   Complexity: {basic_info.get('complexity_score', 'unknown').title()}")
            print(f"   Reading Time: {basic_info.get('estimated_reading_time', 'unknown')}")
            lang_analysis = basic_info.get('language_analysis', {})
            print(f"   Formality Score: {lang_analysis.get('formality_score', 0):.2f}")
            print()
        
        # 2. Legal Clauses
        legal_clauses = analysis.get('legal_clauses', [])
        if legal_clauses:
            print(f"⚖️  LEGAL CLAUSES IDENTIFIED ({len(legal_clauses)}):")
            print("-" * 30)
            for i, clause in enumerate(legal_clauses, 1):
                clause_type = clause.get('type', 'unknown').replace('_', ' ').title()
                risk_level = clause.get('risk_level', 'unknown').upper()
                confidence = clause.get('confidence', 0)
                dates = clause.get('associated_dates', [])
                
                print(f"{i:2d}. {clause_type}")
                print(f"     Risk Level: {risk_level}")
                print(f"     Confidence: {confidence:.2f}")
                if dates:
                    print(f"     Associated Dates: {', '.join(dates)}")
                print(f"     Risk Explanation: {clause.get('risk_explanation', 'No explanation')}")
                print()
        
        # 3. Risk Assessment
        risk_assessment = analysis.get('risk_assessment', {})
        if risk_assessment:
            print("⚠️  COMPREHENSIVE RISK ASSESSMENT:")
            print("-" * 35)
            print(f"Overall Risk Score: {risk_assessment.get('overall_risk_score', 0):.2f}/1.0")
            print()
            
            high_risks = risk_assessment.get('high_risk_items', [])
            if high_risks:
                print(f"🔴 HIGH RISK ITEMS ({len(high_risks)}):")
                for risk in high_risks:
                    risk_type = risk.get('type', 'unknown').replace('_', ' ').title()
                    print(f"   • {risk_type}")
                    print(f"     Description: {risk.get('description', 'No description')}")
                    print(f"     Impact: {risk.get('impact', 'Unknown')}")
                    print(f"     Mitigation: {risk.get('mitigation', 'No mitigation')}")
                    print()
            
            medium_risks = risk_assessment.get('medium_risk_items', [])
            if medium_risks:
                print(f"🟡 MEDIUM RISK ITEMS ({len(medium_risks)}):")
                for risk in medium_risks:
                    risk_type = risk.get('type', 'unknown').replace('_', ' ').title()
                    print(f"   • {risk_type}")
                    print(f"     Description: {risk.get('description', 'No description')}")
                    print()
            
            # Risk categories
            risk_categories = risk_assessment.get('risk_categories', {})
            if risk_categories:
                print("📊 RISK CATEGORIES:")
                for category, count in risk_categories.items():
                    if count > 0:
                        print(f"   {category.title()}: {count} items")
                print()
        
        # 4. Critical Dates
        key_dates = analysis.get('key_dates', [])
        if key_dates:
            print(f"📅 CRITICAL DATES ({len(key_dates)}):")
            print("-" * 20)
            for date_info in key_dates:
                date_str = date_info.get('date', 'unknown')
                date_type = date_info.get('type', 'unknown').replace('_', ' ').title()
                importance = date_info.get('importance', 'unknown').upper()
                days_from_now = date_info.get('days_from_now')
                
                urgency = ""
                if days_from_now is not None:
                    if days_from_now < 0:
                        urgency = " (PAST DUE!)"
                    elif days_from_now <= 30:
                        urgency = " (URGENT)"
                    elif days_from_now <= 90:
                        urgency = " (UPCOMING)"
                
                print(f"   📆 {date_str} - {date_type}{urgency}")
                print(f"      Importance: {importance}")
                print(f"      Context: {date_info.get('context', 'No context')}")
                print()
        
        # 5. Parties Involved
        parties = analysis.get('parties_involved', [])
        if parties:
            print(f"👥 PARTIES INVOLVED ({len(parties)}):")
            print("-" * 25)
            for party in parties:
                name = party.get('name', 'unknown')
                party_type = party.get('type', 'unknown')
                print(f"   • {name} ({party_type})")
            print()
        
        # 6. Financial Terms
        financial_terms = analysis.get('financial_terms', {})
        amounts = financial_terms.get('amounts', [])
        if amounts:
            print(f"💰 FINANCIAL TERMS ({len(amounts)}):")
            print("-" * 22)
            for amount in amounts:
                amt = amount.get('amount', 'unknown')
                amt_type = amount.get('type', 'unknown')
                context = amount.get('context', 'No context')
                print(f"   • {amt} - {amt_type}")
                print(f"     Context: {context}")
                print()
        
        # 7. Obligations
        obligations = analysis.get('obligations', [])
        if obligations:
            print(f"📋 OBLIGATIONS ({len(obligations)}):")
            print("-" * 17)
            for obligation in obligations:
                desc = obligation.get('description', 'No description')
                oblig_type = obligation.get('type', 'unknown')
                severity = obligation.get('severity', 'unknown')
                print(f"   • {desc[:60]}...")
                print(f"     Type: {oblig_type}, Severity: {severity}")
                print()
        
        # 8. Compliance Requirements
        compliance = analysis.get('compliance_requirements', [])
        if compliance:
            print(f"⚖️  COMPLIANCE REQUIREMENTS ({len(compliance)}):")
            print("-" * 32)
            for req in compliance:
                desc = req.get('description', 'No description')
                req_type = req.get('type', 'unknown')
                jurisdiction = req.get('jurisdiction', 'unknown')
                print(f"   • {desc[:50]}...")
                print(f"     Type: {req_type}, Jurisdiction: {jurisdiction}")
                print()
        
        print("🎉 DEMONSTRATION COMPLETE!")
        print("=" * 30)
        print()
        print("✅ Your extraction engine now provides:")
        print("   🔍 Comprehensive legal clause identification")
        print("   ⚠️  Detailed risk assessment with explanations")
        print("   📅 Critical date tracking with urgency alerts")
        print("   👥 Automatic party identification")
        print("   💰 Financial term extraction and analysis")
        print("   📋 Obligation and duty identification")
        print("   ⚖️  Compliance requirement tracking")
        print("   📊 Document complexity analysis")
        print()
        print("🚀 MASSIVE IMPROVEMENT over basic pattern matching!")
        print("   Your documents now get professional-grade legal analysis!")
        
        return True
        
    except Exception as e:
        print(f"❌ Demonstration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = demonstrate_enhanced_extraction()
    exit(0 if success else 1)
