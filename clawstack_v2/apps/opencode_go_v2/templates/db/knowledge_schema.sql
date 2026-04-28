CREATE TABLE IF NOT EXISTS external_knowledge_items (
    id BIGSERIAL PRIMARY KEY,
    source_type TEXT NOT NULL,
    source_url TEXT,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    category TEXT NOT NULL,
    tags TEXT[] DEFAULT '{}',
    usefulness_score INTEGER CHECK (usefulness_score BETWEEN 0 AND 100),
    confidentiality_risk TEXT CHECK (confidentiality_risk IN ('low','medium','high','blocked')),
    adoption_status TEXT CHECK (adoption_status IN ('reject','watch','store_only','propose','dev_implement','prod_candidate')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cae_design_cases (
    id BIGSERIAL PRIMARY KEY,
    domain TEXT NOT NULL,
    model_feature_json JSONB NOT NULL,
    doe_plan_json JSONB,
    cae_solver TEXT,
    result_summary TEXT,
    outcome TEXT CHECK (outcome IN ('success','failure','partial','unknown')),
    failure_category TEXT,
    improvement_action TEXT,
    reusable_lesson TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
