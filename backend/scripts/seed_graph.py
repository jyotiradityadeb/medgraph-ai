import asyncio
from typing import Any

from app.config import get_settings
from app.db.neo4j_client import Neo4jClient


async def run_statement(
    client: Neo4jClient, index: int, label: str, query: str, params: dict[str, Any]
) -> bool:
    try:
        await client.execute_write(query, params)
        print(f"[OK] {index:03d} {label}")
        return True
    except Exception as exc:
        print(f"[FAIL] {index:03d} {label}: {exc}")
        return False


def drug_nodes() -> list[dict[str, Any]]:
    return [
        {
            "id": "drug_aspirin",
            "props": {
                "name": "Aspirin",
                "generic_name": "Acetylsalicylic acid",
                "brand_names": ["Bayer", "Bufferin", "Ecotrin"],
                "drug_class": "NSAID / Antiplatelet",
                "mechanism_of_action": "Irreversibly inhibits COX-1 and COX-2 enzymes, reducing prostaglandin synthesis and thromboxane A2 production",
                "half_life": "3-5 hours (salicylate 6-12 hours at higher doses)",
                "bioavailability": "80-100%",
                "contraindications": [
                    "Active peptic ulcer",
                    "Bleeding disorders",
                    "Children with viral illness",
                    "Third trimester pregnancy",
                ],
                "side_effects": [
                    "GI bleeding",
                    "Tinnitus",
                    "Reye syndrome in children",
                    "Prolonged bleeding time",
                ],
                "pregnancy_category": "D in third trimester",
                "description": "Salicylate drug used for pain relief, fever reduction, inflammation, and antiplatelet therapy in cardiovascular disease prevention",
            },
        },
        {
            "id": "drug_metformin",
            "props": {
                "name": "Metformin",
                "generic_name": "Metformin hydrochloride",
                "brand_names": ["Glucophage", "Glumetza", "Fortamet"],
                "drug_class": "Biguanide antidiabetic",
                "mechanism_of_action": "Activates AMPK, decreasing hepatic glucose production, improving insulin sensitivity in muscle and adipose tissue, decreasing intestinal glucose absorption",
                "half_life": "4-8.7 hours",
                "bioavailability": "50-60%",
                "contraindications": [
                    "eGFR < 30 mL/min",
                    "Iodinated contrast within 48h",
                    "Metabolic acidosis",
                    "Hepatic impairment",
                ],
                "side_effects": [
                    "GI upset",
                    "Diarrhea",
                    "Nausea",
                    "Lactic acidosis (rare)",
                    "B12 deficiency with long-term use",
                ],
                "pregnancy_category": "B",
                "description": "First-line oral antidiabetic for Type 2 Diabetes. Reduces HbA1c by 1-2%. Does not cause hypoglycemia as monotherapy. Weight neutral.",
            },
        },
        {
            "id": "drug_lisinopril",
            "props": {
                "name": "Lisinopril",
                "generic_name": "Lisinopril",
                "brand_names": ["Prinivil", "Zestril"],
                "drug_class": "ACE Inhibitor",
                "mechanism_of_action": "Inhibits angiotensin-converting enzyme, preventing conversion of angiotensin I to angiotensin II, reducing vasoconstriction and aldosterone secretion",
                "half_life": "12 hours",
                "bioavailability": "25%",
                "contraindications": [
                    "Pregnancy",
                    "History of ACE inhibitor angioedema",
                    "Bilateral renal artery stenosis",
                    "Concurrent use with aliskiren in DM",
                ],
                "side_effects": [
                    "Dry cough (10-20%)",
                    "Hyperkalemia",
                    "Angioedema (rare)",
                    "Hypotension",
                    "Acute kidney injury",
                ],
                "pregnancy_category": "D",
                "description": "ACE inhibitor for hypertension, heart failure, post-MI, and diabetic nephropathy. Reduces cardiovascular mortality and slows CKD progression.",
            },
        },
        {
            "id": "drug_warfarin",
            "props": {
                "name": "Warfarin",
                "generic_name": "Warfarin sodium",
                "brand_names": ["Coumadin", "Jantoven"],
                "drug_class": "Vitamin K antagonist anticoagulant",
                "mechanism_of_action": "Inhibits Vitamin K epoxide reductase complex 1 (VKORC1), preventing regeneration of active Vitamin K, inhibiting synthesis of clotting factors II, VII, IX, X",
                "half_life": "36-42 hours",
                "bioavailability": "~100%",
                "contraindications": [
                    "Active bleeding",
                    "Pregnancy",
                    "Severe hepatic disease",
                    "Recent CNS surgery",
                ],
                "side_effects": [
                    "Bleeding (major risk)",
                    "Skin necrosis",
                    "Purple toe syndrome",
                    "Teratogenicity",
                ],
                "pregnancy_category": "X",
                "description": "Oral anticoagulant requiring INR monitoring (target 2-3 for most indications). Multiple drug and food interactions. Genetic variants CYP2C9 and VKORC1 affect dosing.",
            },
        },
        {
            "id": "drug_metoprolol",
            "props": {
                "name": "Metoprolol",
                "generic_name": "Metoprolol succinate / tartrate",
                "brand_names": ["Lopressor", "Toprol-XL"],
                "drug_class": "Cardioselective beta-1 blocker",
                "mechanism_of_action": "Selectively blocks beta-1 adrenergic receptors in heart, reducing heart rate, contractility, and cardiac output. At high doses loses cardioselectivity.",
                "half_life": "3-7 hours (tartrate), 12-24 hours (succinate XL)",
                "bioavailability": "40-50%",
                "contraindications": [
                    "Cardiogenic shock",
                    "Decompensated heart failure",
                    "Sick sinus syndrome without pacemaker",
                    "Severe bradycardia",
                    "Second/third degree AV block",
                ],
                "side_effects": [
                    "Bradycardia",
                    "Fatigue",
                    "Cold extremities",
                    "Bronchospasm (less than non-selective)",
                    "Depression",
                    "Sexual dysfunction",
                ],
                "pregnancy_category": "C",
                "description": "Beta blocker for hypertension, angina, heart failure (HFrEF), post-MI, and rate control in AF. Reduces mortality in heart failure.",
            },
        },
        {
            "id": "drug_atorvastatin",
            "props": {
                "name": "Atorvastatin",
                "generic_name": "Atorvastatin calcium",
                "brand_names": ["Lipitor"],
                "drug_class": "HMG-CoA reductase inhibitor (statin)",
                "mechanism_of_action": "Competitively inhibits HMG-CoA reductase, the rate-limiting enzyme in cholesterol biosynthesis, reducing hepatic cholesterol production and upregulating LDL receptors",
                "half_life": "14 hours (active metabolites up to 20-30 hours)",
                "bioavailability": "14%",
                "contraindications": [
                    "Active liver disease",
                    "Pregnancy",
                    "Breastfeeding",
                    "Unexplained persistent elevation of serum transaminases",
                ],
                "side_effects": [
                    "Myopathy/rhabdomyolysis (rare)",
                    "Elevated liver enzymes",
                    "GI upset",
                    "New-onset diabetes (slight risk)",
                ],
                "pregnancy_category": "X",
                "description": "High-intensity statin reducing LDL by 50%+ at 40-80mg doses. First-line for cardiovascular risk reduction. ASCVD risk reduction independent of baseline LDL.",
            },
        },
        {
            "id": "drug_omeprazole",
            "props": {
                "name": "Omeprazole",
                "generic_name": "Omeprazole",
                "brand_names": ["Prilosec", "Losec"],
                "drug_class": "Proton pump inhibitor",
                "mechanism_of_action": "Irreversibly inhibits H+/K+-ATPase (proton pump) on gastric parietal cells, blocking the final step of acid secretion",
                "half_life": "0.5-1 hour (but duration of action 24+ hours due to irreversible binding)",
                "bioavailability": "30-40% (increases with repeated dosing to ~60%)",
                "contraindications": [
                    "Concurrent use with rilpivirine",
                    "Hypersensitivity to PPIs",
                ],
                "side_effects": [
                    "Headache",
                    "GI upset",
                    "C. difficile risk with long-term use",
                    "Hypomagnesemia",
                    "Reduced B12/calcium absorption",
                    "CKD association with long-term use",
                ],
                "pregnancy_category": "C",
                "description": "PPI for GERD, peptic ulcer disease, H. pylori eradication, and stress ulcer prophylaxis. Most widely prescribed drug class globally.",
            },
        },
        {
            "id": "drug_amoxicillin",
            "props": {
                "name": "Amoxicillin",
                "generic_name": "Amoxicillin trihydrate",
                "brand_names": ["Amoxil", "Trimox"],
                "drug_class": "Aminopenicillin antibiotic",
                "mechanism_of_action": "Beta-lactam antibiotic that inhibits bacterial cell wall synthesis by binding to penicillin-binding proteins (PBPs), preventing peptidoglycan cross-linking",
                "half_life": "1-1.5 hours",
                "bioavailability": "80-90% oral",
                "contraindications": [
                    "Penicillin allergy",
                    "Infectious mononucleosis (risk of rash)",
                ],
                "side_effects": [
                    "Diarrhea",
                    "Nausea",
                    "Rash",
                    "Allergic reactions (anaphylaxis rare)",
                    "C. difficile colitis",
                ],
                "pregnancy_category": "B",
                "description": "Broad-spectrum penicillin for respiratory, urinary, skin infections, H. pylori eradication. First-line for community-acquired pneumonia in outpatients.",
            },
        },
        {
            "id": "drug_insulin_glargine",
            "props": {
                "name": "Insulin Glargine",
                "generic_name": "Insulin glargine",
                "brand_names": ["Lantus", "Basaglar", "Toujeo"],
                "drug_class": "Long-acting insulin analog",
                "mechanism_of_action": "Recombinant human insulin analog with single amino acid substitution. Forms microprecipitates at pH 7.4, slowly releasing monomeric insulin over 24 hours providing peakless basal coverage",
                "half_life": "12-24 hours (no distinct peak)",
                "bioavailability": "Subcutaneous only",
                "contraindications": [
                    "Hypoglycemia",
                    "IV use",
                    "Diabetic ketoacidosis (use short-acting insulin)",
                ],
                "side_effects": [
                    "Hypoglycemia",
                    "Injection site reactions",
                    "Weight gain",
                    "Lipodystrophy",
                ],
                "pregnancy_category": "C",
                "description": "Once-daily basal insulin for Type 1 and Type 2 Diabetes. Provides stable 24-hour coverage. Does not mix with other insulins in same syringe.",
            },
        },
        {
            "id": "drug_sertraline",
            "props": {
                "name": "Sertraline",
                "generic_name": "Sertraline hydrochloride",
                "brand_names": ["Zoloft"],
                "drug_class": "Selective serotonin reuptake inhibitor (SSRI)",
                "mechanism_of_action": "Potently and selectively inhibits neuronal serotonin reuptake, increasing serotonergic transmission. Minimal affinity for muscarinic, histamine, or adrenergic receptors.",
                "half_life": "24-26 hours (active metabolite desmethylsertraline 60-70 hours)",
                "bioavailability": "44%",
                "contraindications": [
                    "MAOIs within 14 days",
                    "Pimozide",
                    "Disulfiram (liquid formulation only)",
                ],
                "side_effects": [
                    "Nausea (common initially)",
                    "Sexual dysfunction",
                    "Insomnia",
                    "Diarrhea",
                    "Serotonin syndrome (overdose/interaction)",
                    "Suicidality risk in youth",
                ],
                "pregnancy_category": "C",
                "description": "Most prescribed SSRI for major depression, OCD, panic disorder, PTSD, social anxiety. Takes 4-6 weeks for full antidepressant effect.",
            },
        },
        {
            "id": "drug_albuterol",
            "props": {
                "name": "Albuterol",
                "generic_name": "Albuterol sulfate (salbutamol)",
                "brand_names": ["Ventolin", "ProAir", "Proventil"],
                "drug_class": "Short-acting beta-2 agonist (SABA) bronchodilator",
                "mechanism_of_action": "Selectively stimulates beta-2 adrenergic receptors in bronchial smooth muscle, causing relaxation and bronchodilation. Onset 5 minutes, duration 4-6 hours.",
                "half_life": "3-8 hours",
                "bioavailability": "Inhaled preferred; oral 30%",
                "contraindications": ["Hypersensitivity", "Tachyarrhythmias (relative)"],
                "side_effects": [
                    "Tachycardia",
                    "Tremor",
                    "Hypokalemia (high doses)",
                    "Palpitations",
                    "Headache",
                ],
                "pregnancy_category": "C",
                "description": "Rescue inhaler for asthma and COPD bronchospasm. PRN use. Frequent use (>2x/week) indicates poor asthma control requiring step-up therapy.",
            },
        },
        {
            "id": "drug_levothyroxine",
            "props": {
                "name": "Levothyroxine",
                "generic_name": "Levothyroxine sodium (L-thyroxine)",
                "brand_names": ["Synthroid", "Levoxyl", "Tirosint"],
                "drug_class": "Thyroid hormone replacement",
                "mechanism_of_action": "Synthetic T4 that is converted peripherally to active T3, binding thyroid hormone nuclear receptors to regulate metabolism, growth, and organ function",
                "half_life": "6-7 days",
                "bioavailability": "40-80% (take on empty stomach)",
                "contraindications": [
                    "Untreated adrenal insufficiency",
                    "Thyrotoxicosis",
                    "Recent MI (relative)",
                ],
                "side_effects": [
                    "Palpitations if overdosed",
                    "Weight loss",
                    "Insomnia",
                    "Heat intolerance",
                    "Osteoporosis with long-term over-replacement",
                    "Atrial fibrillation",
                ],
                "pregnancy_category": "A",
                "description": "Standard treatment for hypothyroidism. Monitor TSH every 6-8 weeks until stable, then annually. Narrow therapeutic index requiring consistent brand/formulation.",
            },
        },
        {
            "id": "drug_amlodipine",
            "props": {
                "name": "Amlodipine",
                "generic_name": "Amlodipine besylate",
                "brand_names": ["Norvasc"],
                "drug_class": "Dihydropyridine calcium channel blocker",
                "mechanism_of_action": "Blocks L-type calcium channels in vascular smooth muscle and cardiac muscle, causing vasodilation, reducing peripheral vascular resistance and blood pressure",
                "half_life": "30-50 hours",
                "bioavailability": "64-90%",
                "contraindications": [
                    "Severe aortic stenosis",
                    "Cardiogenic shock",
                    "Hypersensitivity to dihydropyridines",
                ],
                "side_effects": [
                    "Peripheral edema (dose-dependent)",
                    "Flushing",
                    "Palpitations",
                    "Headache",
                    "Gingival hyperplasia (rare)",
                ],
                "pregnancy_category": "C",
                "description": "Long-acting CCB for hypertension and chronic stable angina. Well tolerated. Edema not due to fluid retention but venodilation — respond to amlodipine dose reduction not diuretics.",
            },
        },
        {
            "id": "drug_furosemide",
            "props": {
                "name": "Furosemide",
                "generic_name": "Furosemide",
                "brand_names": ["Lasix"],
                "drug_class": "Loop diuretic",
                "mechanism_of_action": "Inhibits Na-K-2Cl cotransporter (NKCC2) in thick ascending limb of Loop of Henle, preventing reabsorption of sodium, chloride, and water. Also inhibits carbonic anhydrase.",
                "half_life": "30-120 minutes",
                "bioavailability": "60-70% oral (variable; IV preferred in acute decompensation)",
                "contraindications": ["Anuria", "Sulfonamide allergy (relative)", "Hypovolemia"],
                "side_effects": [
                    "Hypokalemia",
                    "Hyponatremia",
                    "Hypomagnesemia",
                    "Ototoxicity (high doses, especially IV)",
                    "Hyperuricemia",
                    "Metabolic alkalosis",
                    "Dehydration",
                ],
                "pregnancy_category": "C",
                "description": "Potent loop diuretic for edema in heart failure, cirrhosis, nephrotic syndrome, and hypertensive urgency. Electrolyte monitoring essential.",
            },
        },
        {
            "id": "drug_prednisone",
            "props": {
                "name": "Prednisone",
                "generic_name": "Prednisone",
                "brand_names": ["Deltasone", "Rayos"],
                "drug_class": "Synthetic corticosteroid",
                "mechanism_of_action": "Prodrug converted to active prednisolone. Binds glucocorticoid receptors, modulating transcription of anti-inflammatory genes. Suppresses immune response and inflammation.",
                "half_life": "2-3 hours (prednisolone 3-4 hours)",
                "bioavailability": "~80%",
                "contraindications": [
                    "Systemic fungal infections",
                    "Live vaccines during high-dose therapy",
                ],
                "side_effects": [
                    "Hyperglycemia",
                    "Immunosuppression",
                    "Osteoporosis",
                    "Cushing syndrome with long-term use",
                    "Adrenal suppression",
                    "Mood changes",
                    "Weight gain",
                    "Hypertension",
                    "Peptic ulcer",
                ],
                "pregnancy_category": "C",
                "description": "Versatile corticosteroid for inflammatory conditions, autoimmune disease, COPD exacerbations, allergic reactions, and immunosuppression. Taper required after >2 weeks use.",
            },
        },
    ]


def disease_nodes() -> list[dict[str, Any]]:
    return [
        {
            "id": "disease_t2dm",
            "props": {
                "name": "Type 2 Diabetes Mellitus",
                "icd10_code": "E11",
                "icd11_code": "5A11",
                "description": "Chronic metabolic disorder characterized by insulin resistance and relative insulin deficiency, causing hyperglycemia. Progressive beta-cell dysfunction over time.",
                "prevalence": "537 million adults worldwide (2021)",
                "mortality_rate": "6.7 per 100,000",
                "age_of_onset": "Usually >40 but rising in youth",
                "organ_systems": [
                    "Endocrine",
                    "Cardiovascular",
                    "Renal",
                    "Neurological",
                    "Ophthalmologic",
                ],
                "is_chronic": True,
                "is_genetic": True,
                "diagnostic_criteria": "HbA1c ≥6.5% OR fasting glucose ≥126 mg/dL OR 2h glucose ≥200 mg/dL OR random glucose ≥200 with symptoms",
            },
        },
        {
            "id": "disease_hypertension",
            "props": {
                "name": "Hypertension",
                "icd10_code": "I10",
                "icd11_code": "BA00",
                "description": "Sustained elevation of systemic arterial blood pressure (≥130/80 mmHg per AHA 2017 guidelines). Leading modifiable risk factor for cardiovascular disease, stroke, and CKD.",
                "prevalence": "1.28 billion adults worldwide",
                "mortality_rate": "Leading contributor to 10.8 million deaths annually",
                "age_of_onset": "Increases with age; 65% prevalence in adults >65",
                "organ_systems": ["Cardiovascular", "Renal", "Neurological", "Ophthalmologic"],
                "is_chronic": True,
                "is_genetic": True,
            },
        },
        {
            "id": "disease_heart_failure",
            "props": {
                "name": "Heart Failure",
                "icd10_code": "I50",
                "icd11_code": "BD10",
                "description": "Clinical syndrome where the heart cannot pump sufficient blood to meet metabolic demands or does so at elevated filling pressures. Classified as HFrEF (EF<40%), HFmrEF (40-49%), HFpEF (≥50%).",
                "prevalence": "64 million people worldwide",
                "mortality_rate": "50% 5-year mortality in advanced HF",
                "age_of_onset": "Predominantly >65 years",
                "organ_systems": ["Cardiovascular", "Pulmonary", "Renal"],
                "is_chronic": True,
                "is_genetic": False,
            },
        },
        {
            "id": "disease_af",
            "props": {
                "name": "Atrial Fibrillation",
                "icd10_code": "I48",
                "icd11_code": "BC81",
                "description": "Most common sustained cardiac arrhythmia. Irregular and often rapid heart rate from disorganized atrial electrical activity. Major risk factor for stroke, heart failure, and death.",
                "prevalence": "37.5 million worldwide",
                "mortality_rate": "Increases all-cause mortality 1.5-3.5x",
                "age_of_onset": "Rare <50, prevalence doubles each decade after 50",
                "organ_systems": ["Cardiovascular", "Neurological"],
                "is_chronic": True,
                "is_genetic": False,
            },
        },
        {
            "id": "disease_copd",
            "props": {
                "name": "COPD",
                "icd10_code": "J44",
                "icd11_code": "CA22",
                "description": "Chronic Obstructive Pulmonary Disease. Preventable and treatable lung disease causing persistent airflow limitation. Includes emphysema and chronic bronchitis. GOLD staging I-IV by FEV1.",
                "prevalence": "391 million worldwide",
                "mortality_rate": "3rd leading cause of death globally",
                "age_of_onset": "Usually >40, peak diagnosis 55-65",
                "organ_systems": ["Pulmonary", "Cardiovascular"],
                "is_chronic": True,
                "is_genetic": False,
            },
        },
        {
            "id": "disease_mdd",
            "props": {
                "name": "Major Depressive Disorder",
                "icd10_code": "F32",
                "icd11_code": "6A70",
                "description": "Common mood disorder causing persistent depressed mood or anhedonia lasting ≥2 weeks with neurovegetative symptoms. Leading cause of disability worldwide.",
                "prevalence": "280 million worldwide",
                "mortality_rate": "15x suicide rate vs general population",
                "age_of_onset": "Peak onset 25-49; bimodal in adolescents",
                "organ_systems": ["Neurological", "Endocrine"],
                "is_chronic": True,
                "is_genetic": True,
            },
        },
        {
            "id": "disease_hypothyroidism",
            "props": {
                "name": "Hypothyroidism",
                "icd10_code": "E03.9",
                "icd11_code": "5A00",
                "description": "Underproduction of thyroid hormones T3 and T4. Most common cause in iodine-sufficient countries is Hashimoto thyroiditis (autoimmune). Causes metabolic slowdown.",
                "prevalence": "5% of US population; 10-20% of women >60",
                "age_of_onset": "Any age; most common in middle-aged women",
                "organ_systems": ["Endocrine", "Cardiovascular", "Neurological"],
                "is_chronic": True,
                "is_genetic": True,
            },
        },
        {
            "id": "disease_pneumonia",
            "props": {
                "name": "Pneumonia",
                "icd10_code": "J18",
                "icd11_code": "CA40",
                "description": "Acute lower respiratory tract infection causing alveolar inflammation and consolidation. Community-acquired (CAP) vs hospital-acquired (HAP) classification. S. pneumoniae most common bacterial cause.",
                "prevalence": "450 million cases annually",
                "mortality_rate": "5-10% CAP requiring hospitalization; >30% ICU",
                "age_of_onset": "All ages; highest mortality in <5 and >65",
                "organ_systems": ["Pulmonary"],
                "is_chronic": False,
                "is_genetic": False,
            },
        },
        {
            "id": "disease_peptic_ulcer",
            "props": {
                "name": "Peptic Ulcer Disease",
                "icd10_code": "K27",
                "icd11_code": "DA60",
                "description": "Break in gastric or duodenal mucosa extending through muscularis mucosa. Caused by H. pylori infection or NSAID use in 95% of cases. Duodenal ulcers more common.",
                "prevalence": "4 million new cases annually in US",
                "age_of_onset": "Any age; duodenal 30-50, gastric 55-65",
                "organ_systems": ["Gastrointestinal"],
                "is_chronic": True,
                "is_genetic": False,
            },
        },
        {
            "id": "disease_dyslipidemia",
            "props": {
                "name": "Dyslipidemia",
                "icd10_code": "E78",
                "icd11_code": "5C80",
                "description": "Abnormal blood lipid levels including elevated LDL, low HDL, or elevated triglycerides. Major modifiable cardiovascular risk factor. Primary (genetic) or secondary causes.",
                "prevalence": "Affects >50% of US adults",
                "age_of_onset": "Primary: childhood; Secondary: any age",
                "organ_systems": ["Cardiovascular", "Endocrine"],
                "is_chronic": True,
                "is_genetic": True,
            },
        },
        {
            "id": "disease_asthma",
            "props": {
                "name": "Asthma",
                "icd10_code": "J45",
                "icd11_code": "CA23",
                "description": "Chronic inflammatory airway disease with variable and reversible airflow obstruction. Characterized by bronchospasm, mucus hypersecretion, and airway hyperresponsiveness.",
                "prevalence": "262 million worldwide",
                "age_of_onset": "Often childhood onset; can develop at any age",
                "organ_systems": ["Pulmonary"],
                "is_chronic": True,
                "is_genetic": True,
            },
        },
        {
            "id": "disease_ckd",
            "props": {
                "name": "Chronic Kidney Disease",
                "icd10_code": "N18",
                "icd11_code": "GB61",
                "description": "Progressive loss of kidney function over months to years. Staged by eGFR (G1-G5) and albuminuria (A1-A3). Complications include anemia, metabolic acidosis, electrolyte imbalances, cardiovascular disease.",
                "prevalence": "700 million worldwide",
                "mortality_rate": "Leading cause of death 11th globally",
                "age_of_onset": "Increases with age; DM and HTN are leading causes",
                "organ_systems": ["Renal", "Cardiovascular", "Endocrine", "Hematologic"],
                "is_chronic": True,
                "is_genetic": False,
            },
        },
        {
            "id": "disease_gerd",
            "props": {
                "name": "GERD",
                "icd10_code": "K21",
                "icd11_code": "DD90",
                "description": "Gastroesophageal reflux disease due to reflux of gastric contents into the esophagus causing troublesome symptoms and mucosal injury.",
                "is_chronic": True,
                "is_genetic": False,
            },
        },
        {
            "id": "disease_active_bleeding",
            "props": {
                "name": "Active Bleeding",
                "icd10_code": "R58",
                "icd11_code": "MD93",
                "description": "Ongoing hemorrhage from any site requiring urgent hemostatic assessment and intervention.",
                "is_chronic": False,
                "is_genetic": False,
            },
        },
        {
            "id": "disease_decomp_hf",
            "props": {
                "name": "Decompensated Heart Failure",
                "icd10_code": "I50.9",
                "icd11_code": "BD10.0",
                "description": "Acute worsening of heart failure with pulmonary or systemic congestion requiring urgent stabilization.",
                "is_chronic": False,
                "is_genetic": False,
            },
        },
        {
            "id": "disease_pregnancy",
            "props": {
                "name": "Pregnancy",
                "icd10_code": "Z33",
                "icd11_code": "JA00",
                "description": "Physiologic state of gestation with medication safety considerations due to maternal and fetal risk.",
                "is_chronic": False,
                "is_genetic": False,
            },
        },
    ]


def symptom_nodes() -> list[dict[str, Any]]:
    return [
        {
            "id": "sym_chest_pain",
            "name": "Chest pain",
            "description": "Pain or discomfort in the chest with variable quality and intensity. It can reflect benign musculoskeletal causes or life-threatening cardiopulmonary disease.",
            "body_system": "Cardiovascular",
            "severity_scale": 8,
            "is_specific": False,
        },
        {
            "id": "sym_dyspnea",
            "name": "Dyspnea",
            "description": "Subjective sensation of breathing difficulty or air hunger. It commonly occurs in cardiopulmonary disease and worsens with exertion or fluid overload.",
            "body_system": "Pulmonary",
            "severity_scale": 8,
            "is_specific": False,
        },
        {
            "id": "sym_fatigue",
            "name": "Fatigue",
            "description": "Persistent lack of energy affecting daily function. It is nonspecific and appears in metabolic, endocrine, cardiac, and psychiatric disorders.",
            "body_system": "Systemic",
            "severity_scale": 6,
            "is_specific": False,
        },
        {
            "id": "sym_palpitations",
            "name": "Palpitations",
            "description": "Awareness of abnormal heartbeat sensation such as racing, pounding, or irregular beats. Episodes may be benign or linked to clinically significant arrhythmias.",
            "body_system": "Cardiovascular",
            "severity_scale": 6,
            "is_specific": False,
        },
        {
            "id": "sym_syncope",
            "name": "Syncope",
            "description": "Transient loss of consciousness from global cerebral hypoperfusion. Cardiac syncope carries high risk and needs urgent evaluation.",
            "body_system": "Neurological",
            "severity_scale": 9,
            "is_specific": False,
        },
        {
            "id": "sym_polyuria",
            "name": "Polyuria",
            "description": "Excessive urine output beyond normal daily volume. It often reflects osmotic diuresis from hyperglycemia or renal concentrating defects.",
            "body_system": "Renal",
            "severity_scale": 5,
            "is_specific": False,
        },
        {
            "id": "sym_polydipsia",
            "name": "Polydipsia",
            "description": "Persistent excessive thirst with increased fluid intake. It frequently accompanies polyuria in uncontrolled diabetes.",
            "body_system": "Endocrine",
            "severity_scale": 5,
            "is_specific": False,
        },
        {
            "id": "sym_weight_gain",
            "name": "Weight gain",
            "description": "Increase in body weight over baseline. It may reflect endocrine dysfunction, fluid retention, or medication effects.",
            "body_system": "Endocrine",
            "severity_scale": 4,
            "is_specific": False,
        },
        {
            "id": "sym_weight_loss",
            "name": "Weight loss",
            "description": "Unintentional reduction in body weight. It can signal catabolic states, malabsorption, malignancy, or uncontrolled diabetes.",
            "body_system": "Systemic",
            "severity_scale": 6,
            "is_specific": False,
        },
        {
            "id": "sym_cough",
            "name": "Cough",
            "description": "Protective airway reflex triggered by airway irritation or inflammation. Chronic cough may indicate COPD, asthma, reflux, or medication adverse effects.",
            "body_system": "Pulmonary",
            "severity_scale": 4,
            "is_specific": False,
        },
        {
            "id": "sym_wheezing",
            "name": "Wheezing",
            "description": "High-pitched expiratory airflow sound from narrowed airways. It is common in asthma and COPD exacerbations.",
            "body_system": "Pulmonary",
            "severity_scale": 6,
            "is_specific": True,
        },
        {
            "id": "sym_edema",
            "name": "Peripheral edema",
            "description": "Dependent swelling from interstitial fluid accumulation, usually in lower extremities. It occurs with heart failure, venous insufficiency, renal disease, or medication effects.",
            "body_system": "Cardiovascular",
            "severity_scale": 5,
            "is_specific": False,
        },
        {
            "id": "sym_orthopnea",
            "name": "Orthopnea",
            "description": "Shortness of breath when lying flat that improves on sitting up. It is a classic sign of elevated left-sided filling pressures in heart failure.",
            "body_system": "Cardiovascular",
            "severity_scale": 7,
            "is_specific": True,
        },
        {
            "id": "sym_diaphoresis",
            "name": "Diaphoresis",
            "description": "Excessive sweating not explained by ambient temperature or exertion. It can accompany ischemia, hypoglycemia, infection, or autonomic stress.",
            "body_system": "Autonomic",
            "severity_scale": 5,
            "is_specific": False,
        },
        {
            "id": "sym_tremor",
            "name": "Tremor",
            "description": "Involuntary rhythmic oscillatory movement of a body part. It may be physiologic, medication-induced, or associated with neurologic disease.",
            "body_system": "Neurological",
            "severity_scale": 4,
            "is_specific": False,
        },
        {
            "id": "sym_cold_intolerance",
            "name": "Cold intolerance",
            "description": "Heightened sensitivity to cold temperatures. It is commonly reported in hypothyroidism due to reduced thermogenesis.",
            "body_system": "Endocrine",
            "severity_scale": 4,
            "is_specific": True,
        },
        {
            "id": "sym_melena",
            "name": "Melena",
            "description": "Black tarry stool due to upper gastrointestinal bleeding. It indicates blood digestion in the GI tract and requires urgent assessment.",
            "body_system": "Gastrointestinal",
            "severity_scale": 9,
            "is_specific": True,
        },
        {
            "id": "sym_heartburn",
            "name": "Heartburn",
            "description": "Burning retrosternal discomfort often after meals or when supine. It is a hallmark reflux symptom and may coexist with peptic disease.",
            "body_system": "Gastrointestinal",
            "severity_scale": 4,
            "is_specific": False,
        },
        {
            "id": "sym_hemoptysis",
            "name": "Hemoptysis",
            "description": "Expectoration of blood from the lower respiratory tract. Severity ranges from streaking to life-threatening airway hemorrhage.",
            "body_system": "Pulmonary",
            "severity_scale": 8,
            "is_specific": True,
        },
        {
            "id": "sym_bradycardia",
            "name": "Bradycardia",
            "description": "Heart rate below normal resting range, often <60 bpm in adults. It may be physiologic or medication-related but can cause dizziness or syncope when severe.",
            "body_system": "Cardiovascular",
            "severity_scale": 6,
            "is_specific": False,
        },
        {
            "id": "sym_hypokalemia",
            "name": "Hypokalemia",
            "description": "Low serum potassium level that can impair neuromuscular and cardiac conduction. It often results from renal loss, especially with loop diuretics.",
            "body_system": "Electrolyte",
            "severity_scale": 7,
            "is_specific": True,
        },
        {
            "id": "sym_hemorrhage",
            "name": "Hemorrhage",
            "description": "Clinically significant blood loss from vascular rupture or impaired hemostasis. It can present externally or internally and may cause hemodynamic instability.",
            "body_system": "Hematologic",
            "severity_scale": 10,
            "is_specific": True,
        },
    ]


def lab_nodes() -> list[dict[str, Any]]:
    return [
        {
            "id": "lab_hba1c",
            "name": "HbA1c",
            "unit": "%",
            "normal_range_min": 4.0,
            "normal_range_max": 5.7,
            "description": "Glycated hemoglobin reflecting 90-day average blood glucose",
        },
        {
            "id": "lab_fasting_glucose",
            "name": "Fasting glucose",
            "unit": "mg/dL",
            "normal_range_min": 70.0,
            "normal_range_max": 99.0,
            "description": "Plasma glucose after fasting, used in diabetes diagnosis",
        },
        {
            "id": "lab_bnp",
            "name": "BNP",
            "unit": "pg/mL",
            "normal_range_min": 0.0,
            "normal_range_max": 100.0,
            "description": "B-type natriuretic peptide; elevated in heart failure",
        },
        {
            "id": "lab_troponin",
            "name": "Troponin I",
            "unit": "ng/mL",
            "normal_range_min": 0.0,
            "normal_range_max": 0.04,
            "description": "Cardiac injury biomarker for myocardial necrosis",
        },
        {
            "id": "lab_tsh",
            "name": "TSH",
            "unit": "mIU/L",
            "normal_range_min": 0.4,
            "normal_range_max": 4.0,
            "description": "Pituitary thyroid-stimulating hormone for thyroid axis assessment",
        },
        {
            "id": "lab_free_t4",
            "name": "Free T4",
            "unit": "ng/dL",
            "normal_range_min": 0.8,
            "normal_range_max": 1.8,
            "description": "Unbound thyroxine level reflecting thyroid hormone availability",
        },
        {
            "id": "lab_inr",
            "name": "INR",
            "unit": "ratio",
            "normal_range_min": 0.8,
            "normal_range_max": 1.2,
            "therapeutic_range": "2.0-3.0 on warfarin",
            "description": "Standardized prothrombin time for anticoagulation monitoring",
        },
        {
            "id": "lab_egfr",
            "name": "eGFR",
            "unit": "mL/min/1.73m2",
            "normal_range_min": 60.0,
            "normal_range_max": 140.0,
            "description": "Estimated glomerular filtration rate indicating renal function",
        },
        {
            "id": "lab_ldl",
            "name": "LDL cholesterol",
            "unit": "mg/dL",
            "normal_range_min": 0.0,
            "normal_range_max": 100.0,
            "description": "Low-density lipoprotein cholesterol used in ASCVD risk management",
        },
        {
            "id": "lab_potassium",
            "name": "Potassium",
            "unit": "mEq/L",
            "normal_range_min": 3.5,
            "normal_range_max": 5.0,
            "description": "Serum potassium concentration critical for cardiac conduction",
        },
    ]


def gene_nodes() -> list[dict[str, Any]]:
    return [
        {
            "id": "gene_cyp2c9",
            "name": "CYP2C9",
            "description": "Cytochrome P450 enzyme gene involved in warfarin and NSAID metabolism",
        },
        {
            "id": "gene_vkorc1",
            "name": "VKORC1",
            "description": "Warfarin target gene; variants strongly affect anticoagulant sensitivity",
        },
        {
            "id": "gene_tcf7l2",
            "name": "TCF7L2",
            "description": "Transcription factor gene with one of the strongest Type 2 Diabetes genetic associations",
        },
        {
            "id": "gene_adrb1",
            "name": "ADRB1",
            "description": "Beta-1 adrenergic receptor gene influencing beta-blocker response",
        },
        {
            "id": "gene_ace",
            "name": "ACE",
            "description": "Angiotensin-converting enzyme gene; insertion/deletion polymorphism linked to cardiovascular risk",
        },
    ]


def relationship_specs() -> list[dict[str, Any]]:
    rels: list[dict[str, Any]] = []

    def add(
        src_label: str,
        src_id: str,
        rel_type: str,
        dst_label: str,
        dst_id: str,
        props: dict[str, Any],
    ):
        rels.append(
            {
                "src_label": src_label,
                "src_id": src_id,
                "rel_type": rel_type,
                "dst_label": dst_label,
                "dst_id": dst_id,
                "props": props,
            }
        )

    add(
        "Drug",
        "drug_aspirin",
        "TREATS",
        "Disease",
        "disease_heart_failure",
        {"indication": "prophylaxis", "evidence_level": "A"},
    )
    add(
        "Drug",
        "drug_metformin",
        "TREATS",
        "Disease",
        "disease_t2dm",
        {"indication": "first-line", "efficacy_score": 0.85, "evidence_level": "A"},
    )
    add(
        "Drug",
        "drug_lisinopril",
        "TREATS",
        "Disease",
        "disease_hypertension",
        {"indication": "first-line", "efficacy_score": 0.82, "evidence_level": "A"},
    )
    add(
        "Drug",
        "drug_lisinopril",
        "TREATS",
        "Disease",
        "disease_heart_failure",
        {"indication": "reduces mortality", "efficacy_score": 0.88, "evidence_level": "A"},
    )
    add(
        "Drug",
        "drug_lisinopril",
        "TREATS",
        "Disease",
        "disease_ckd",
        {"indication": "nephroprotective in DM", "evidence_level": "A"},
    )
    add(
        "Drug",
        "drug_warfarin",
        "TREATS",
        "Disease",
        "disease_af",
        {"indication": "anticoagulation", "evidence_level": "A"},
    )
    add(
        "Drug",
        "drug_metoprolol",
        "TREATS",
        "Disease",
        "disease_hypertension",
        {"evidence_level": "A"},
    )
    add(
        "Drug",
        "drug_metoprolol",
        "TREATS",
        "Disease",
        "disease_heart_failure",
        {"indication": "reduces mortality HFrEF", "evidence_level": "A"},
    )
    add(
        "Drug",
        "drug_metoprolol",
        "TREATS",
        "Disease",
        "disease_af",
        {"indication": "rate control", "evidence_level": "A"},
    )
    add(
        "Drug",
        "drug_atorvastatin",
        "TREATS",
        "Disease",
        "disease_dyslipidemia",
        {"indication": "high-intensity", "evidence_level": "A"},
    )
    add(
        "Drug",
        "drug_omeprazole",
        "TREATS",
        "Disease",
        "disease_peptic_ulcer",
        {"evidence_level": "A"},
    )
    add("Drug", "drug_omeprazole", "TREATS", "Disease", "disease_gerd", {"evidence_level": "A"})
    add(
        "Drug",
        "drug_albuterol",
        "TREATS",
        "Disease",
        "disease_asthma",
        {"indication": "rescue", "evidence_level": "A"},
    )
    add(
        "Drug",
        "drug_albuterol",
        "TREATS",
        "Disease",
        "disease_copd",
        {"indication": "bronchodilation", "evidence_level": "A"},
    )
    add(
        "Drug",
        "drug_levothyroxine",
        "TREATS",
        "Disease",
        "disease_hypothyroidism",
        {"indication": "replacement", "evidence_level": "A"},
    )
    add(
        "Drug",
        "drug_sertraline",
        "TREATS",
        "Disease",
        "disease_mdd",
        {"indication": "first-line SSRI", "evidence_level": "A"},
    )
    add(
        "Drug",
        "drug_furosemide",
        "TREATS",
        "Disease",
        "disease_heart_failure",
        {"indication": "symptom relief", "evidence_level": "A"},
    )
    add(
        "Drug",
        "drug_insulin_glargine",
        "TREATS",
        "Disease",
        "disease_t2dm",
        {"indication": "basal insulin", "evidence_level": "A"},
    )
    add(
        "Drug",
        "drug_prednisone",
        "TREATS",
        "Disease",
        "disease_copd",
        {"indication": "exacerbation", "evidence_level": "A"},
    )
    add(
        "Drug",
        "drug_prednisone",
        "TREATS",
        "Disease",
        "disease_asthma",
        {"indication": "acute exacerbation", "evidence_level": "A"},
    )
    add(
        "Drug",
        "drug_amlodipine",
        "TREATS",
        "Disease",
        "disease_hypertension",
        {"evidence_level": "A"},
    )

    add(
        "Drug",
        "drug_warfarin",
        "INTERACTS_WITH",
        "Drug",
        "drug_aspirin",
        {
            "severity": "MAJOR",
            "mechanism": "Additive anticoagulation and antiplatelet effect, increases bleeding risk significantly",
            "interaction_type": "pharmacodynamic",
        },
    )
    add(
        "Drug",
        "drug_warfarin",
        "INTERACTS_WITH",
        "Drug",
        "drug_amoxicillin",
        {
            "severity": "MODERATE",
            "mechanism": "Gut flora alteration reduces Vitamin K production, potentiates warfarin effect",
            "interaction_type": "pharmacodynamic",
        },
    )
    add(
        "Drug",
        "drug_metformin",
        "INTERACTS_WITH",
        "Drug",
        "drug_furosemide",
        {
            "severity": "MODERATE",
            "mechanism": "Furosemide increases lactic acid risk; monitor renal function",
            "interaction_type": "pharmacokinetic",
        },
    )
    add(
        "Drug",
        "drug_lisinopril",
        "INTERACTS_WITH",
        "Drug",
        "drug_furosemide",
        {
            "severity": "MODERATE",
            "mechanism": "Additive hypotension; first-dose effect. Monitor BP closely.",
            "interaction_type": "pharmacodynamic",
        },
    )
    add(
        "Drug",
        "drug_sertraline",
        "INTERACTS_WITH",
        "Drug",
        "drug_aspirin",
        {
            "severity": "MODERATE",
            "mechanism": "Both inhibit platelet aggregation via serotonin pathway; increased GI bleeding risk",
            "interaction_type": "pharmacodynamic",
        },
    )
    add(
        "Drug",
        "drug_atorvastatin",
        "INTERACTS_WITH",
        "Drug",
        "drug_amlodipine",
        {
            "severity": "MODERATE",
            "mechanism": "Amlodipine inhibits CYP3A4, increasing atorvastatin levels up to 77%; myopathy risk",
            "interaction_type": "pharmacokinetic",
        },
    )
    add(
        "Drug",
        "drug_prednisone",
        "INTERACTS_WITH",
        "Drug",
        "drug_metformin",
        {
            "severity": "MODERATE",
            "mechanism": "Corticosteroids cause hyperglycemia, opposing metformin effect; titration needed",
            "interaction_type": "pharmacodynamic",
        },
    )

    add(
        "Drug",
        "drug_metformin",
        "CONTRAINDICATED_FOR",
        "Disease",
        "disease_ckd",
        {
            "reason": "eGFR <30: lactic acidosis risk; use with caution eGFR 30-45",
            "severity": "MAJOR",
        },
    )
    add(
        "Drug",
        "drug_warfarin",
        "CONTRAINDICATED_FOR",
        "Disease",
        "disease_active_bleeding",
        {"reason": "High risk of major hemorrhage", "severity": "MAJOR"},
    )
    add(
        "Drug",
        "drug_metoprolol",
        "CONTRAINDICATED_FOR",
        "Disease",
        "disease_decomp_hf",
        {"reason": "Negative inotropy in unstable decompensation", "severity": "MAJOR"},
    )
    add(
        "Drug",
        "drug_aspirin",
        "CONTRAINDICATED_FOR",
        "Disease",
        "disease_peptic_ulcer",
        {"reason": "Inhibits protective prostaglandins", "severity": "MAJOR"},
    )
    add(
        "Drug",
        "drug_lisinopril",
        "CONTRAINDICATED_FOR",
        "Disease",
        "disease_pregnancy",
        {"reason": "Fetal renal toxicity and teratogenic risk", "severity": "MAJOR"},
    )

    add(
        "Disease",
        "disease_heart_failure",
        "MANIFESTS_AS",
        "Symptom",
        "sym_dyspnea",
        {"frequency": "95%", "specificity": "low"},
    )
    add(
        "Disease",
        "disease_heart_failure",
        "MANIFESTS_AS",
        "Symptom",
        "sym_edema",
        {"frequency": "70%", "specificity": "moderate"},
    )
    add(
        "Disease",
        "disease_heart_failure",
        "MANIFESTS_AS",
        "Symptom",
        "sym_orthopnea",
        {"frequency": "60%", "specificity": "high"},
    )
    add(
        "Disease",
        "disease_heart_failure",
        "MANIFESTS_AS",
        "Symptom",
        "sym_fatigue",
        {"frequency": "90%"},
    )
    add(
        "Disease", "disease_af", "MANIFESTS_AS", "Symptom", "sym_palpitations", {"frequency": "80%"}
    )
    add("Disease", "disease_af", "MANIFESTS_AS", "Symptom", "sym_syncope", {"frequency": "15%"})
    add("Disease", "disease_af", "MANIFESTS_AS", "Symptom", "sym_fatigue", {"frequency": "70%"})
    add("Disease", "disease_t2dm", "MANIFESTS_AS", "Symptom", "sym_polyuria", {"frequency": "60%"})
    add(
        "Disease", "disease_t2dm", "MANIFESTS_AS", "Symptom", "sym_polydipsia", {"frequency": "60%"}
    )
    add(
        "Disease",
        "disease_t2dm",
        "MANIFESTS_AS",
        "Symptom",
        "sym_weight_loss",
        {"frequency": "40%"},
    )
    add("Disease", "disease_copd", "MANIFESTS_AS", "Symptom", "sym_dyspnea", {"frequency": "100%"})
    add("Disease", "disease_copd", "MANIFESTS_AS", "Symptom", "sym_cough", {"frequency": "90%"})
    add("Disease", "disease_copd", "MANIFESTS_AS", "Symptom", "sym_wheezing", {"frequency": "60%"})
    add(
        "Disease",
        "disease_hypothyroidism",
        "MANIFESTS_AS",
        "Symptom",
        "sym_weight_gain",
        {"frequency": "60%"},
    )
    add(
        "Disease",
        "disease_hypothyroidism",
        "MANIFESTS_AS",
        "Symptom",
        "sym_cold_intolerance",
        {"frequency": "70%"},
    )
    add(
        "Disease",
        "disease_hypothyroidism",
        "MANIFESTS_AS",
        "Symptom",
        "sym_fatigue",
        {"frequency": "85%"},
    )
    add(
        "Disease",
        "disease_hypothyroidism",
        "MANIFESTS_AS",
        "Symptom",
        "sym_bradycardia",
        {"frequency": "50%"},
    )
    add(
        "Disease",
        "disease_peptic_ulcer",
        "MANIFESTS_AS",
        "Symptom",
        "sym_heartburn",
        {"frequency": "65%"},
    )
    add(
        "Disease",
        "disease_peptic_ulcer",
        "MANIFESTS_AS",
        "Symptom",
        "sym_melena",
        {"frequency": "20%", "specificity": "high", "severity": "high"},
    )

    add(
        "Disease",
        "disease_t2dm",
        "DIAGNOSED_BY",
        "LabTest",
        "lab_hba1c",
        {"sensitivity": 0.90, "specificity": 0.98},
    )
    add(
        "Disease",
        "disease_t2dm",
        "DIAGNOSED_BY",
        "LabTest",
        "lab_fasting_glucose",
        {"sensitivity": 0.85, "specificity": 0.95},
    )
    add(
        "Disease",
        "disease_heart_failure",
        "DIAGNOSED_BY",
        "LabTest",
        "lab_bnp",
        {"sensitivity": 0.95, "specificity": 0.73},
    )
    add(
        "Disease",
        "disease_hypothyroidism",
        "DIAGNOSED_BY",
        "LabTest",
        "lab_tsh",
        {"sensitivity": 0.98, "specificity": 0.92},
    )
    add(
        "Disease",
        "disease_hypothyroidism",
        "DIAGNOSED_BY",
        "LabTest",
        "lab_free_t4",
        {"sensitivity": 0.85, "specificity": 0.95},
    )
    add("Disease", "disease_ckd", "DIAGNOSED_BY", "LabTest", "lab_egfr", {"gold_standard": True})
    add(
        "Disease",
        "disease_dyslipidemia",
        "DIAGNOSED_BY",
        "LabTest",
        "lab_ldl",
        {"guideline_based": True},
    )

    add(
        "Drug",
        "drug_metoprolol",
        "CAUSES",
        "Symptom",
        "sym_bradycardia",
        {"frequency": "common", "severity": "moderate"},
    )
    add(
        "Drug",
        "drug_furosemide",
        "CAUSES",
        "Symptom",
        "sym_hypokalemia",
        {"frequency": "common", "severity": "moderate"},
    )
    add(
        "Drug",
        "drug_lisinopril",
        "CAUSES",
        "Symptom",
        "sym_cough",
        {"frequency": "10-20%", "severity": "mild", "mechanism": "Bradykinin accumulation"},
    )
    add(
        "Drug",
        "drug_warfarin",
        "CAUSES",
        "Symptom",
        "sym_hemorrhage",
        {"frequency": "dose-dependent", "severity": "severe"},
    )
    add(
        "Drug",
        "drug_levothyroxine",
        "CAUSES",
        "Symptom",
        "sym_palpitations",
        {"context": "when overdosed", "frequency": "20%"},
    )

    add(
        "Gene",
        "gene_cyp2c9",
        "AFFECTS",
        "Drug",
        "drug_warfarin",
        {"mechanism": "Poor metabolizers require lower doses; *2 and *3 alleles reduce metabolism"},
    )
    add(
        "Gene",
        "gene_vkorc1",
        "AFFECTS",
        "Drug",
        "drug_warfarin",
        {"mechanism": "1639G>A variant increases warfarin sensitivity; requires dose reduction"},
    )
    add(
        "Gene",
        "gene_tcf7l2",
        "AFFECTS",
        "Disease",
        "disease_t2dm",
        {"mechanism": "Strong inherited susceptibility signal for Type 2 Diabetes"},
    )
    add(
        "Gene",
        "gene_adrb1",
        "AFFECTS",
        "Drug",
        "drug_metoprolol",
        {"mechanism": "Arg389Gly variant affects beta-blocker response"},
    )

    add(
        "Disease",
        "disease_t2dm",
        "COMORBID_WITH",
        "Disease",
        "disease_hypertension",
        {"strength": "high"},
    )
    add("Disease", "disease_t2dm", "COMORBID_WITH", "Disease", "disease_ckd", {"strength": "high"})
    add(
        "Disease",
        "disease_t2dm",
        "COMORBID_WITH",
        "Disease",
        "disease_dyslipidemia",
        {"strength": "high"},
    )
    add(
        "Disease",
        "disease_hypertension",
        "COMORBID_WITH",
        "Disease",
        "disease_ckd",
        {"strength": "high"},
    )
    add(
        "Disease",
        "disease_hypertension",
        "COMORBID_WITH",
        "Disease",
        "disease_heart_failure",
        {"strength": "high"},
    )
    add(
        "Disease",
        "disease_hypertension",
        "COMORBID_WITH",
        "Disease",
        "disease_af",
        {"strength": "moderate"},
    )
    add(
        "Disease",
        "disease_ckd",
        "COMORBID_WITH",
        "Disease",
        "disease_heart_failure",
        {"strength": "high"},
    )
    add(
        "Disease",
        "disease_copd",
        "COMORBID_WITH",
        "Disease",
        "disease_heart_failure",
        {"strength": "moderate"},
    )
    add(
        "Disease",
        "disease_asthma",
        "COMORBID_WITH",
        "Disease",
        "disease_copd",
        {"strength": "moderate"},
    )
    add(
        "Disease",
        "disease_mdd",
        "COMORBID_WITH",
        "Disease",
        "disease_t2dm",
        {"strength": "moderate"},
    )

    add("Drug", "drug_warfarin", "MONITORED_BY", "LabTest", "lab_inr", {"target_range": "2.0-3.0"})
    add(
        "Drug",
        "drug_metformin",
        "MONITORED_BY",
        "LabTest",
        "lab_hba1c",
        {"purpose": "glycemic control"},
    )
    add(
        "Drug",
        "drug_insulin_glargine",
        "MONITORED_BY",
        "LabTest",
        "lab_hba1c",
        {"purpose": "glycemic control"},
    )
    add(
        "Drug",
        "drug_lisinopril",
        "MONITORED_BY",
        "LabTest",
        "lab_potassium",
        {"purpose": "hyperkalemia surveillance"},
    )
    add(
        "Drug",
        "drug_furosemide",
        "MONITORED_BY",
        "LabTest",
        "lab_potassium",
        {"purpose": "hypokalemia surveillance"},
    )
    add(
        "Drug",
        "drug_lisinopril",
        "MONITORED_BY",
        "LabTest",
        "lab_egfr",
        {"purpose": "renal function trend"},
    )
    add(
        "Drug",
        "drug_metformin",
        "MONITORED_BY",
        "LabTest",
        "lab_egfr",
        {"purpose": "renal dosing safety"},
    )
    add(
        "Drug",
        "drug_atorvastatin",
        "MONITORED_BY",
        "LabTest",
        "lab_ldl",
        {"purpose": "lipid response"},
    )
    add(
        "Drug",
        "drug_levothyroxine",
        "MONITORED_BY",
        "LabTest",
        "lab_tsh",
        {"purpose": "dose titration"},
    )
    add(
        "Drug",
        "drug_levothyroxine",
        "MONITORED_BY",
        "LabTest",
        "lab_free_t4",
        {"purpose": "hormone replacement adequacy"},
    )

    add(
        "Drug",
        "drug_albuterol",
        "CAUSES",
        "Symptom",
        "sym_tremor",
        {"frequency": "common", "severity": "mild"},
    )
    add(
        "Drug",
        "drug_albuterol",
        "CAUSES",
        "Symptom",
        "sym_palpitations",
        {"frequency": "common", "severity": "mild"},
    )
    add(
        "Drug",
        "drug_amlodipine",
        "CAUSES",
        "Symptom",
        "sym_edema",
        {"frequency": "dose-dependent", "severity": "moderate"},
    )
    add(
        "Drug",
        "drug_prednisone",
        "CAUSES",
        "Symptom",
        "sym_weight_gain",
        {"frequency": "common with prolonged use", "severity": "moderate"},
    )
    add(
        "Gene",
        "gene_ace",
        "AFFECTS",
        "Drug",
        "drug_lisinopril",
        {"mechanism": "ACE I/D polymorphism may alter blood pressure response"},
    )
    add(
        "Gene",
        "gene_ace",
        "AFFECTS",
        "Disease",
        "disease_hypertension",
        {"mechanism": "ACE variants associated with cardiovascular risk profiles"},
    )

    return rels


async def main() -> None:
    settings = get_settings()
    client = Neo4jClient(settings.NEO4J_URI, settings.NEO4J_USER, settings.NEO4J_PASSWORD)

    print("Connecting to Neo4j...")
    if not await client.verify_connectivity():
        print("Neo4j connectivity failed.")
        await client.close()
        return

    print("Creating schema...")
    await client.create_schema()

    statements: list[tuple[str, str, dict[str, Any]]] = []

    for item in drug_nodes():
        statements.append(
            (
                f"Drug {item['id']}",
                "MERGE (d:Drug {id: $id}) SET d += $props",
                {"id": item["id"], "props": item["props"]},
            )
        )

    for item in disease_nodes():
        statements.append(
            (
                f"Disease {item['id']}",
                "MERGE (d:Disease {id: $id}) SET d += $props",
                {"id": item["id"], "props": item["props"]},
            )
        )

    for item in symptom_nodes():
        statements.append(
            (
                f"Symptom {item['id']}",
                "MERGE (s:Symptom {id: $id}) SET s += $props",
                {"id": item["id"], "props": {k: v for k, v in item.items() if k != "id"}},
            )
        )

    for item in lab_nodes():
        statements.append(
            (
                f"LabTest {item['id']}",
                "MERGE (l:LabTest {id: $id}) SET l += $props",
                {"id": item["id"], "props": {k: v for k, v in item.items() if k != "id"}},
            )
        )

    for item in gene_nodes():
        statements.append(
            (
                f"Gene {item['id']}",
                "MERGE (g:Gene {id: $id}) SET g += $props",
                {"id": item["id"], "props": {k: v for k, v in item.items() if k != "id"}},
            )
        )

    rels = relationship_specs()
    print(f"Prepared {len(rels)} relationship statements.")
    for idx, rel in enumerate(rels, start=1):
        query = (
            f"MATCH (a:{rel['src_label']} {{id: $src_id}}) "
            f"MATCH (b:{rel['dst_label']} {{id: $dst_id}}) "
            f"MERGE (a)-[r:{rel['rel_type']}]->(b) "
            "SET r += $props"
        )
        statements.append(
            (
                f"REL {idx:03d} {rel['src_id']} -[{rel['rel_type']}]-> {rel['dst_id']}",
                query,
                {"src_id": rel["src_id"], "dst_id": rel["dst_id"], "props": rel["props"]},
            )
        )

    print(f"Running {len(statements)} total MERGE statements...")
    successes = 0
    failures = 0

    for index, (label, query, params) in enumerate(statements, start=1):
        ok = await run_statement(client, index, label, query, params)
        if ok:
            successes += 1
        else:
            failures += 1

    print(f"Completed seed run. Successes: {successes}, Failures: {failures}")
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
