"""
Jobxplo — Stage 5: role taxonomy mapping.

Reads every raw company file in data/raw/*.json (from Stage 4) and
adds a `role_category` field to each job, mapped from the messy
`raw_title` into one of the fixed categories in data/role_taxonomy.json.

Two-step mapping, cheapest first:
  1. Keyword rules   - if the title contains an obvious keyword
                       ("data engineer", "recruiter", etc.), map it
                       directly. Free, fast, handles most titles.
  2. Fuzzy fallback   - for titles that don't match any keyword rule,
                       use Python's built-in difflib to find the closest
                       canonical role by text similarity. No extra
                       libraries needed to install.

This does NOT overwrite the raw title anywhere - `raw_title` is kept
untouched and always shown to the user later. `role_category` is only
used for filtering.

Usage:
    python scripts/map_roles.py
"""

import json
import difflib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
TAXONOMY_FILE = ROOT / "data" / "role_taxonomy.json"

# Step 1: keyword rules.
# Order matters - more specific keywords should come before general ones.
# Each canonical role maps to a list of keywords checked (case-insensitive)
# against the raw title.
KEYWORD_RULES = [
    # Engineering
    #("Site Reliability Engineer", ["site reliability", "sre"]),
    #("DevOps Engineer", ["devops", "dev ops"]),
    #("Platform Engineer", ["platform engineer", "platform engineering"]),
    #("Infrastructure Engineer", ["infrastructure engineer", "infra engineer"]),
    #("Cloud Engineer", ["cloud engineer", "cloud infrastructure"]),
    #("Cloud Architect", ["cloud architect", "solutions architect", "solution architect"]),
    #("Software Engineer", ["software engineer", "software developer", "swe"]),
    #("Backend Engineer", ["backend", "back-end", "back end engineer"]),
    #("Frontend Engineer", ["frontend", "front-end", "front end engineer"]),
    #("Full Stack Engineer", ["full stack", "fullstack", "full stack developer"]),
    #("Mobile Engineer", ["mobile engineer", "ios engineer", "android engineer"]),
    ("Embedded Engineer", [
    "embedded engineer",
    "embedded software engineer",
    "embedded software",
    "embedded developer",
    "embedded systems engineer",
    "embedded systems developer",
    "firmware engineer",
    "firmware developer",
    "microcontroller engineer",
    "mcu engineer",
    "rtos engineer"
    ]),

    ("Firmware Engineer", [
        "firmware engineer",
        "firmware developer",
        "firmware software engineer",
        "embedded firmware engineer",
        "device firmware engineer",
        "low level software engineer",
        "bios engineer",
        "bootloader engineer"
    ]),

    ("Systems Engineer", [
        "systems engineer",
        "system engineer",
        "systems software engineer",
        "system integration engineer",
        "systems development engineer",
        "computer systems engineer",
        "technical systems engineer"
    ]),

    ("Network Engineer", [
        "network engineer",
        "network administrator",
        "network specialist",
        "network infrastructure engineer",
        "network operations engineer",
        "noc engineer",
        "network support engineer",
        "routing engineer",
        "switching engineer",
        "wireless network engineer"
    ]),

    ("Platform Engineer", [
        "platform engineer",
        "platform engineering",
        "developer platform engineer",
        "internal platform engineer",
        "cloud platform engineer",
        "platform infrastructure engineer",
        "developer experience engineer",
        "devex engineer",
        "developer productivity engineer",
        "kubernetes platform engineer",
        "container platform engineer",
        "infrastructure platform engineer"
    ]),

    ("Infrastructure Engineer", [
        "infrastructure engineer",
        "infra engineer",
        "cloud infrastructure engineer",
        "infrastructure developer",
        "systems infrastructure engineer",
        "datacenter engineer",
        "server infrastructure engineer",
        "production infrastructure engineer",
        "it infrastructure engineer",
        "infrastructure operations engineer"
    ]),

    ("Cloud Architect", [
        "cloud architect",
        "cloud solutions architect",
        "cloud solution architect",
        "solutions architect",
        "solution architect",
        "enterprise cloud architect",
        "cloud infrastructure architect",
        "aws solutions architect",
        "azure solutions architect",
        "gcp cloud architect",
        "cloud consultant architect"
    ]),

    ("Release Engineer", [
        "release engineer",
        "release management engineer",
        "software release engineer",
        "release automation engineer",
        "deployment engineer",
        "ci/cd engineer",
        "continuous delivery engineer",
        "continuous deployment engineer"
    ]),

    ("Build Engineer", [
        "build engineer",
        "build and release engineer",
        "software build engineer",
        "compilation engineer",
        "build automation engineer",
        "developer tools engineer"
    ]),

    ("Automation Engineer", [
        "automation engineer",
        "automation software engineer",
        "test automation engineer",
        "process automation engineer",
        "workflow automation engineer",
        "rpa engineer",
        "automation developer"
    ]),

    ("Solutions Engineer", [
        "solutions engineer",
        "sales engineer",
        "solutions consultant",
        "technical solutions engineer",
        "customer solutions engineer",
        "implementation engineer",
        "pre sales engineer",
        "presales engineer"
    ]),

    ("Support Engineer", [
        "support engineer",
        "technical support engineer",
        "production support engineer",
        "application support engineer",
        "software support engineer",
        "customer support engineer",
        "technical support specialist",
        "support specialist"
    ]),

    ("Application Engineer", [
        "application engineer",
        "applications engineer",
        "application software engineer",
        "application support engineer",
        "application development engineer"
    ]),

    ("Integration Engineer", [
        "integration engineer",
        "integration developer",
        "systems integration engineer",
        "api integration engineer",
        "software integration engineer",
        "middleware engineer"
    ]),

    ("Performance Engineer", [
        "performance engineer",
        "performance software engineer",
        "performance optimization engineer",
        "performance testing engineer",
        "application performance engineer",
        "systems performance engineer"
    ]),

    ("Reliability Engineer", [
        "reliability engineer",
        "software reliability engineer",
        "service reliability engineer",
        "production reliability engineer",
        "site reliability engineer",
        "sre"
    ]),

        # Programming Languages
    ("Python Developer", [
        "python developer",
        "python engineer",
        "python software engineer",
        "python backend developer",
        "python backend engineer",
        "python programmer",
        "python application developer",
        "python web developer",
        "django developer",
        "flask developer",
        "fastapi developer",
        "python api developer"
    ]),

    ("Java Developer", [
        "java developer",
        "java engineer",
        "java software engineer",
        "java backend developer",
        "java backend engineer",
        "java application developer",
        "j2ee developer",
        "jee developer",
        "spring developer",
        "spring boot developer",
        "java microservices developer"
    ]),

    ("C++ Developer", [
        "c++ developer",
        "c++ engineer",
        "cpp developer",
        "cpp engineer",
        "c plus plus developer",
        "c++ software engineer",
        "c++ programmer",
        "embedded c++ developer"
    ]),

    ("C# Developer", [
        "c# developer",
        "c# engineer",
        "c sharp developer",
        "csharp developer",
        "c# software engineer",
        "dotnet c# developer"
    ]),

    (".NET Developer", [
        ".net developer",
        "dotnet developer",
        ".net engineer",
        "dot net developer",
        "asp.net developer",
        "asp.net core developer",
        ".net core developer",
        "c# .net developer",
        "microsoft .net developer"
    ]),

    ("Go Developer", [
        "golang",
        "go developer",
        "go engineer",
        "golang developer",
        "golang engineer",
        "go software engineer",
        "go backend developer"
    ]),

    ("Rust Developer", [
        "rust developer",
        "rust engineer",
        "rust software engineer",
        "rust programmer",
        "systems rust developer"
    ]),

    ("PHP Developer", [
        "php developer",
        "php engineer",
        "php software developer",
        "php web developer",
        "laravel developer",
        "symfony developer",
        "wordpress developer",
        "wordpress php developer"
    ]),

    ("Ruby Developer", [
        "ruby developer",
        "ruby engineer",
        "ruby on rails",
        "rails developer",
        "ror developer",
        "ruby software engineer"
    ]),

    ("Node.js Developer", [
        "nodejs",
        "node.js",
        "node developer",
        "node js developer",
        "node.js developer",
        "node backend developer",
        "nodejs engineer",
        "express.js developer",
        "express developer"
    ]),

    ("React Developer", [
        "react developer",
        "react engineer",
        "reactjs developer",
        "react.js developer",
        "react frontend developer",
        "react software engineer",
        "next.js developer",
        "nextjs developer"
    ]),

    ("Angular Developer", [
        "angular developer",
        "angular engineer",
        "angularjs developer",
        "angular frontend developer",
        "typescript angular developer"
    ]),

    ("Vue.js Developer", [
        "vue developer",
        "vue.js developer",
        "vuejs developer",
        "vue engineer",
        "vue frontend developer",
        "nuxt developer",
        "nuxt.js developer"
    ]),

    ("Flutter Developer", [
        "flutter developer",
        "flutter engineer",
        "flutter mobile developer",
        "dart developer",
        "dart engineer"
    ]),

    ("React Native Developer", [
        "react native",
        "react native developer",
        "react native engineer",
        "react native mobile developer"
    ]),

    ("iOS Developer", [
        "ios developer",
        "ios engineer",
        "ios software engineer",
        "swift developer",
        "swift engineer",
        "objective-c developer",
        "objective c developer",
        "iphone developer",
        "ipad developer"
    ]),

    ("Android Developer", [
        "android developer",
        "android engineer",
        "android software engineer",
        "kotlin developer",
        "kotlin engineer",
        "android application developer",
        "android app developer"
    ]),

        # Data
    ("Big Data Engineer", [
        "big data engineer",
        "big data developer",
        "big data engineer",
        "spark engineer",
        "hadoop engineer",
        "hadoop developer",
        "apache spark engineer",
        "spark developer",
        "big data analytics engineer",
        "distributed systems engineer",
        "data processing engineer",
        "data platform engineer",
        "mapreduce developer",
        "hive developer",
        "hbase developer",
        "kafka engineer"
    ]),


    ("Analytics Engineer", [
        "analytics engineer",
        "data analytics engineer",
        "analytics developer",
        "business analytics engineer",
        "dbt engineer",
        "dbt developer",
        "modern analytics engineer",
        "metrics engineer"
    ]),


    ("Business Intelligence Engineer", [
        "bi engineer",
        "business intelligence engineer",
        "business intelligence developer",
        "bi analyst",
        "business intelligence analyst",
        "reporting engineer",
        "reporting developer",
        "dashboard engineer",
        "insights engineer"
    ]),


    ("BI Developer", [
        "bi developer",
        "business intelligence developer",
        "power bi developer",
        "powerbi developer",
        "tableau developer",
        "tableau engineer",
        "qlik developer",
        "looker developer",
        "dashboard developer",
        "report developer",
        "reporting developer"
    ]),


    ("ETL Developer", [
        "etl developer",
        "etl engineer",
        "etl programmer",
        "data integration developer",
        "data pipeline developer",
        "data pipeline engineer",
        "batch processing developer",
        "informatica developer",
        "ssis developer",
        "talend developer",
        "ab initio developer",
        "data warehouse developer"
    ]),


    ("Database Engineer", [
        "database engineer",
        "database developer",
        "database software engineer",
        "sql engineer",
        "database specialist",
        "database architect",
        "data platform engineer",
        "database reliability engineer",
        "database performance engineer"
    ]),


    ("Database Administrator", [
        "database administrator",
        "database admin",
        "dba",
        "sql dba",
        "oracle dba",
        "mysql dba",
        "postgresql dba",
        "database operations engineer",
        "database support engineer",
        "database manager"
    ]),


    ("Data Architect", [
        "data architect",
        "enterprise data architect",
        "cloud data architect",
        "big data architect",
        "data solutions architect",
        "data warehouse architect",
        "data platform architect",
        "information architect"
    ]),


    ("Data Quality Engineer", [
        "data quality engineer",
        "data quality analyst",
        "data validation engineer",
        "data testing engineer",
        "data integrity engineer",
        "data governance engineer",
        "data accuracy analyst",
        "data reliability engineer"
    ]),


    ("Data Governance", [
        "data governance",
        "data governance analyst",
        "data governance engineer",
        "data steward",
        "data management",
        "master data management",
        "mdm",
        "metadata management",
        "data compliance",
        "data policy analyst",
        "information governance"
    ]),

    # AI / ML
    #("Machine Learning Engineer", ["machine learning", "ml engineer", "mle"]),
    ("AI Engineer", [
        "ai engineer",
        "artificial intelligence engineer",
        "artificial intelligence developer",
        "ai developer",
        "ai software engineer",
        "machine intelligence engineer",
        "intelligent systems engineer",
        "applied ai engineer",
        "ai solutions engineer"
    ]),


    ("Generative AI Engineer", [
        "generative ai engineer",
        "generative ai",
        "genai engineer",
        "gen ai engineer",
        "genai developer",
        "llm engineer",
        "llm developer",
        "large language model engineer",
        "large language model developer",
        "foundation model engineer",
        "ai application engineer",
        "rag engineer",
        "retrieval augmented generation engineer",
        "prompt engineering with llms",
        "llm application developer"
    ]),


    ("Prompt Engineer", [
        "prompt engineer",
        "ai prompt engineer",
        "llm prompt engineer",
        "prompt designer",
        "prompt specialist",
        "prompt developer",
        "generative ai prompt engineer"
    ]),


    ("NLP Engineer", [
        "nlp engineer",
        "natural language processing engineer",
        "natural language processing",
        "nlp developer",
        "nlp scientist",
        "language model engineer",
        "computational linguist",
        "text analytics engineer",
        "speech nlp engineer",
        "conversational ai engineer",
        "chatbot engineer"
    ]),


    ("Computer Vision Engineer", [
        "computer vision engineer",
        "computer vision",
        "cv engineer",
        "vision engineer",
        "computer vision developer",
        "image processing engineer",
        "image recognition engineer",
        "deep learning vision engineer",
        "opencv engineer",
        "autonomous vision engineer"
    ]),


    ("Research Scientist", [
        "research scientist",
        "ai researcher",
        "ml researcher",
        "machine learning researcher",
        "research engineer",
        "deep learning researcher",
        "computer science researcher",
        "applied scientist",
        "research scientist ai",
        "research scientist machine learning"
    ]),

    # Security
    #("Security Engineer", ["security engineer", "application security", "appsec", "infosec"]),
    ("Cyber Security Engineer", [
        "cyber security engineer",
        "cybersecurity engineer",
        "cyber security",
        "cybersecurity",
        "information security engineer",
        "infosec engineer",
        "security engineering",
        "security infrastructure engineer",
        "network security engineer",
        "application security engineer",
        "security operations engineer"
    ]),


    ("SOC Analyst", [
        "soc analyst",
        "security operations center analyst",
        "security operations analyst",
        "soc engineer",
        "soc specialist",
        "cyber security analyst",
        "threat monitoring analyst",
        "incident monitoring analyst",
        "security monitoring analyst",
        "siem analyst"
    ]),


    ("Security Analyst", [
        "security analyst",
        "information security analyst",
        "infosec analyst",
        "cyber security analyst",
        "cybersecurity analyst",
        "security operations analyst",
        "threat analyst",
        "vulnerability analyst",
        "risk analyst",
        "security assessment analyst"
        "fraud intelligence",
        "fraud analyst",
        "trust and safety",
        "risk analyst"
    ]),


    ("Penetration Tester", [
        "penetration tester",
        "penetration testing",
        "pentester",
        "pen tester",
        "ethical hacker",
        "offensive security engineer",
        "offensive security analyst",
        "red team engineer",
        "red team operator",
        "security researcher",
        "vulnerability researcher"
    ]),


    ("IAM Engineer", [
        "identity and access management",
        "iam engineer",
        "identity access management engineer",
        "identity engineer",
        "access management engineer",
        "identity security engineer",
        "privileged access management engineer",
        "pam engineer",
        "okta engineer",
        "azure ad engineer",
        "entra id engineer"
    ]),


    ("Cloud Security Engineer", [
        "cloud security engineer",
        "cloud security specialist",
        "cloud security analyst",
        "cloud cybersecurity engineer",
        "aws security engineer",
        "azure security engineer",
        "gcp security engineer",
        "cloud infrastructure security engineer",
        "cloud compliance engineer",
        "cloud security architect"
    ]),

# QA

    ("Automation Test Engineer", [
        "automation tester",
        "automation test engineer",
        "test automation engineer",
        "qa automation engineer",
        "automation qa engineer",
        "automated testing engineer",
        "selenium tester",
        "automation engineer qa",
        "sdet",
        "software development engineer in test",
        "test automation developer"
    ]),


    ("Manual Tester", [
        "manual tester",
        "manual testing",
        "manual qa tester",
        "manual qa engineer",
        "quality analyst",
        "software tester",
        "test analyst",
        "functional tester",
        "functional testing engineer"
    ]),


    ("Performance Tester", [
        "performance tester",
        "load tester",
        "performance testing engineer",
        "performance test engineer",
        "load testing engineer",
        "stress tester",
        "stress testing engineer",
        "jmeter tester",
        "performance engineer"
    ]),



    # Design

    ("UI Designer", [
        "ui designer",
        "user interface designer",
        "interface designer",
        "ui design specialist",
        "ui visual designer"
    ]),


    ("UX Designer", [
        "ux designer",
        "user experience designer",
        "ux specialist",
        "experience designer",
        "ux design specialist"
    ]),


    ("Graphic Designer", [
        "graphic designer",
        "visual graphic designer",
        "creative graphic designer",
        "brand graphic designer",
        "graphic design specialist"
    ]),


    ("Visual Designer", [
        "visual designer",
        "visual design specialist",
        "digital visual designer",
        "brand designer",
        "creative designer"
    ]),


    ("UX Researcher", [
        "ux researcher",
        "user experience researcher",
        "user researcher",
        "design researcher",
        "customer experience researcher"
    ]),


    ("Interaction Designer", [
        "interaction designer",
        "interaction design specialist",
        "product interaction designer",
        "human computer interaction designer",
        "hci designer"
    ]),



    # Product

    ("Technical Product Manager", [
        "technical product manager",
        "technical pm",
        "tpm",
        "software product manager",
        "engineering product manager",
        "platform product manager"
    ]),


    ("Product Owner", [
        "product owner",
        "technical product owner",
        "scrum product owner",
        "agile product owner",
        "product lead"
    ]),


    ("Engineering Manager", [
        "engineering manager",
        "eng manager",
        "software engineering manager",
        "technical engineering manager",
        "development manager",
        "software development manager"
    ]),



    # Sales

    ("Sales Manager", [
        "sales manager",
        "regional sales manager",
        "territory sales manager",
        "sales lead",
        "sales director",
        "sales supervisor"
    ]),


    ("Account Manager", [
        "account manager",
        "enterprise accounts",
        "enterprise account",
        "account associate",
        "strategic accounts",
        "key accounts"
    ]),

    ("Business Development Representative", [
        "business development representative",
        "bdr",
        "business development rep",
        "sales development representative",
        "sdr",
        "lead generation representative"
    ]),


    ("Business Development Manager", [
        "business development manager",
        "business development executive",
        "bd manager",
        "growth business manager",
        "partnership manager"
    ]),


    ("Inside Sales", [
        "inside sales",
        "inside sales representative",
        "inside sales executive",
        "inside sales associate",
        "remote sales representative"
    ]),


    ("Enterprise Sales", [
        "enterprise sales",
        "enterprise account executive",
        "enterprise sales manager",
        "strategic sales manager",
        "b2b enterprise sales"
    ]),


    ("Pre Sales Engineer", [
        "pre sales engineer",
        "presales engineer",
        "pre-sales engineer",
        "sales engineer",
        "solutions engineer",
        "technical sales engineer",
        "solution consultant"
    ]),

# Customer Success

    ("Customer Success Engineer", [
        "customer success engineer",
        "technical customer success engineer",
        "customer success technical engineer",
        "customer success specialist",
        "customer success technical specialist",
        "customer solutions engineer"
    ]),


    ("Customer Support", [
        "customer support",
        "customer service",
        "customer support specialist",
        "customer service representative",
        "customer care representative",
        "support specialist",
        "client support",
        "customer experience associate",
        "cx associate"
    ]),


    ("Technical Support Engineer", [
        "technical support engineer",
        "technical support specialist",
        "tech support engineer",
        "technical support",
        "application support engineer",
        "product support engineer",
        "customer support engineer",
        "it support engineer",
        "support engineer"
    ]),



# Marketing

    ("Digital Marketing", [
        "digital marketing",
        "digital marketing specialist",
        "digital marketing executive",
        "online marketing specialist",
        "internet marketing specialist",
        "digital marketing manager"
    ]),


    ("SEO Specialist", [
        "seo specialist",
        "seo analyst",
        "seo manager",
        "search engine optimization",
        "organic search specialist",
        "seo strategist"
    ]),


    ("SEM Specialist", [
        "sem specialist",
        "search engine marketing specialist",
        "paid search specialist",
        "ppc specialist",
        "google ads specialist",
        "paid media specialist"
    ]),


    ("Performance Marketing", [
        "performance marketing",
        "performance marketing specialist",
        "growth marketing specialist",
        "paid marketing specialist",
        "digital performance marketer",
        "conversion rate optimization specialist",
        "cro specialist"
    ]),


    ("Social Media Manager", [
        "social media manager",
        "social media specialist",
        "social media strategist",
        "social media executive",
        "community manager",
        "social media coordinator"
    ]),


    ("Email Marketing", [
        "email marketing",
        "email marketing specialist",
        "email marketing manager",
        "crm marketing specialist",
        "lifecycle marketing specialist",
        "marketing automation specialist"
    ]),


    ("Brand Manager", [
        "brand manager",
        "brand marketing manager",
        "brand strategist",
        "brand specialist",
        "product marketing manager",
        "brand executive"
    ]),



    # HR

    ("HR Generalist", [
        "hr generalist",
        "human resources generalist",
        "hr specialist",
        "hr associate",
        "people specialist",
        "employee relations specialist"
    ]),


    ("People Operations", [
        "people operations",
        "people ops",
        "people operations specialist",
        "people operations manager",
        "employee experience specialist",
            "recruiting systems",
        "talent operations",
        "workforce operations"
        "employee success"
    ]),



    # Finance

    ("Financial Controller", [
        "financial controller",
        "finance controller",
        "financial control manager",
        "corporate controller",
        "accounting controller"
    ]),


    ("Investment Analyst", [
        "investment analyst",
        "equity analyst",
        "research analyst",
        "financial investment analyst",
        "portfolio analyst",
        "investment associate"
    ]),


    ("Auditor", [
        "auditor",
        "internal auditor",
        "external auditor",
        "audit analyst",
        "audit associate",
        "financial auditor",
        "compliance auditor"
    ]),


    ("Tax Consultant", [
        "tax consultant",
        "tax analyst",
        "tax advisor",
        "tax associate",
        "tax specialist",
        "corporate tax consultant"
    ]),



    # Legal

    ("Compliance Officer", [
        "compliance officer",
        "compliance analyst",
        "compliance specialist",
        "regulatory compliance officer",
        "risk compliance analyst",
        "governance compliance specialist"
            "public policy",
        "regulatory policy",
        "policy analyst"
    ]),


    ("Privacy Engineer", [
        "privacy engineer",
        "data privacy engineer",
        "privacy analyst",
        "privacy specialist",
        "privacy technology engineer",
        "privacy by design engineer",
        "information privacy engineer"
    ]),

    # Operations

    ("Operations Analyst", [
        "operations analyst",
        "business operations analyst",
        "ops analyst",
        "operations associate",
        "process analyst",
        "operational analyst",
        "business process analyst",
        "operations specialist"
    ]),


    ("Office Manager", [
        "office manager",
        "office administrator",
        "administrative manager",
        "workplace manager",
        "office operations manager",
        "facility coordinator",
        "administrative coordinator"
    ]),


    ("Supply Chain Manager", [
        "supply chain manager",
        "supply chain specialist",
        "supply chain analyst",
        "supply chain lead",
        "supply chain operations manager",
        "logistics and supply chain manager",
        "supply planning manager"
    ]),


    ("Procurement Manager", [
        "procurement manager",
        "procurement specialist",
        "procurement analyst",
        "purchasing manager",
        "strategic sourcing manager",
        "sourcing specialist",
        "vendor management specialist"
    ]),


    ("Logistics Manager", [
        "logistics manager",
        "logistics specialist",
        "logistics analyst",
        "logistics coordinator",
        "transportation manager",
        "warehouse operations manager",
        "distribution manager"
    ]),



    # Consulting

    ("Consultant", [
        "consultant",
        "advisor",
        "consulting analyst"
    ]),


    ("Business Consultant", [
        "business consultant",
        "business advisor",
        "management consultant",
        "strategy consultant",
        "business transformation consultant",
        "business process consultant"
    ]),


    ("Solutions Consultant", [
        "solutions consultant",
        "solution consultant",
        "solutions advisor",
        "technical solutions consultant",
        "implementation consultant",
        "pre sales consultant",
        "presales consultant"
    ]),


    ("Technical Consultant", [
        "technical consultant",
        "technology consultant",
        "it consultant",
        "software consultant",
        "technical advisor",
        "implementation consultant"
    ]),



    # Documentation

    ("Documentation Engineer", [
        "documentation engineer",
        "technical documentation engineer",
        "documentation specialist",
        "documentation developer",
        "developer documentation engineer",
        "api documentation engineer"
    ]),



    # Leadership

    ("Executive Assistant", [
        "executive assistant",
        "executive coordinator",
        "administrative assistant",
        "personal assistant",
        "executive secretary",
        "chief of staff assistant"
    ]),


    ("Chief Executive Officer", [
        "chief executive officer",
        "ceo",
        "chief executive",
        "company founder ceo"
    ]),


    ("Chief Technology Officer", [
        "chief technology officer",
        "cto",
        "chief technical officer",
        "technology officer"
    ]),


    ("Chief Operating Officer", [
        "chief operating officer",
        "coo",
        "operations officer"
    ]),


    ("Chief Financial Officer", [
        "chief financial officer",
        "cfo",
        "finance officer"
    ]),


    ("Vice President Engineering", [
        "vp engineering",
        "vice president engineering",
        "vice president of engineering",
        "vp of engineering",
        "engineering vice president"
    ]),


    ("Director of Engineering", [
        "director of engineering",
        "engineering director",
        "director software engineering",
        "director of software engineering",
        "software engineering director"
    ]),


    ("Founder", [
        "founder",
        "co-founder",
        "cofounder",
        "startup founder",
        "company founder"
    ]),

    ("Software Engineer", [
    "software engineer",
    "software developer",
    "developer",
    "application engineer",
    "applications engineer",
    "platform engineer",
    "infrastructure engineer",
    "systems engineer",
    "system engineer",
    "embedded engineer",
    "embedded software",
    "firmware engineer",
    "firmware developer",
    "python developer",
    "java developer",
    "golang",
    "go developer",
    "c++ developer",
    "c# developer",
    ".net developer",
    "dotnet developer",
    "php developer",
    "laravel developer",
    "ruby developer",
    "rails developer",
    "node developer",
    "node.js",
    "nodejs",
    "react developer",
    "angular developer",
    "vue developer",
    "flutter developer",
    "react native",
    "ios developer",
    "android developer",
    "swift developer",
    "kotlin developer",
    "staff software engineer",
    "principal software engineer",
    "lead software engineer",
    "senior software engineer",
    "software engineer i",
    "software engineer ii",
    "software engineer iii",
    "software engineer iv",
    "member of technical staff",
    "mts",
    "engineer, software"
    ]),


    ("Frontend Engineer", [
    "frontend",
    "front-end",
    "front end",
    "ui engineer",
    "web engineer",
    "frontend developer",
    "react engineer",
    "angular engineer",
    "vue engineer"
    ]),

    ("Backend Engineer", [
    "backend",
    "back-end",
    "back end",
    "backend developer",
    "api engineer",
    "server engineer"
    ]),

    ("Full Stack Engineer", [
    "full stack",
    "fullstack",
    "full stack developer",
    "full stack engineer"
    ]),

    ("Mobile Engineer", [
    "mobile engineer",
    "mobile developer",
    "android engineer",
    "android developer",
    "ios engineer",
    "ios developer",
    "swift",
    "kotlin",
    "react native",
    "flutter"
    ]),

    ("Data Engineer", [
    "data engineer",
    "data engineering",
    "big data",
    "etl",
    "spark",
    "hadoop",
    "airflow",
    "databricks",
    "analytics engineer",
    "data platform",
    "data infrastructure",
    "data architect",
    "database engineer",
    "database administrator",
    "dba"
    ]),

    ("Data Analyst", [
    "data analyst",
    "business intelligence",
    "bi developer",
    "bi engineer",
    "power bi",
    "tableau",
    "reporting analyst",
    "report analyst",
    "analytics analyst"
    ]),

    ("Data Scientist", [
    "data scientist",
    "data science",
    "decision scientist",
    "quantitative analyst"
    ]),

    ("Machine Learning Engineer", [
    "machine learning",
    "ml engineer",
    "mle",
    "artificial intelligence",
    "ai engineer",
    "genai",
    "llm",
    "computer vision",
    "nlp",
    "deep learning",
    "prompt engineer"
    ]),

    ("DevOps Engineer", [
    "devops",
    "dev ops",
    "release engineer",
    "build engineer",
    "ci/cd",
    "deployment engineer"
    ]),

    ("Site Reliability Engineer", [
    "site reliability",
    "sre",
    "production engineer",
    "reliability engineer"
    ]),

    ("Cloud Engineer", [
    "cloud engineer",
    "cloud architect",
    "solutions architect",
    "solution architect",
    "aws",
    "azure",
    "gcp",
    "cloud infrastructure"
    ]),

    ("Security Engineer", [
    "security engineer",
    "security analyst",
    "cyber security",
    "cybersecurity",
    "application security",
    "appsec",
    "infosec",
    "soc analyst",
    "penetration tester",
    "pentester",
    "ethical hacker",
    "iam engineer",
    "cloud security"
    ]),

    ("QA Engineer", [
    "qa",
    "quality assurance",
    "test engineer",
    "sdet",
    "automation tester",
    "manual tester",
    "performance tester",
    "test automation"
    ]),

    ("Product Manager", [
    "product manager",
    "technical product manager",
    "group product manager",
    "associate product manager",
    "platform product manager",
    "product platform manager",
    "product owner",
    "pm"
    ]),

    ("Product Designer", [
    "product designer",
    "interaction designer",
    "visual designer"
    ]),

    ("UI/UX Designer", [
    "ui designer",
    "ux designer",
    "ui/ux",
    "ux/ui",
    "graphic designer",
    "ux researcher"
    ]),


    ("Program Manager", [
    "program manager",
    "tpm"
    ]),

    ("Technical Program Manager", [
        "technical program manager",
        "technical program management",
        "tpm",
        "engineering program manager",
        "technical project manager"
    ]),



    ("Project Manager", [
    "project manager",
    "delivery manager",
    "scrum master"
    ]),

    ("Business Analyst", [
    "business analyst",
    "business systems analyst",
    "functional analyst"
    ]),

    ("Sales Executive", [
    "sales executive",
    "sales manager",
    "inside sales",
    "enterprise sales",
    "business development",
    "account manager"
    ]),

    ("Account Executive", [
    "account executive",
    "enterprise account executive"
    ]),


    ("Sales Development Representative", [
    "sales development",
    "sdr",
    "business development representative",
    "bdr"
    ]),

    ("Customer Success Manager", [
    "customer success",
    "customer experience",
    "customer success engineer"
    ]),

    ("Support Engineer", [
    "support engineer",
    "technical support",
    "customer support",
    "technical account manager",
    "tam"
    ]),

    ("Marketing Manager", [
    "marketing manager",
    "digital marketing",
    "brand manager",
    "marketing lead"
    ]),

    ("Content Marketing", [
        "content marketing",
        "content writer",
        "copywriter",
        "technical writer"
    ]),

    ("Growth Marketing", [
        "growth marketing",
        "performance marketing",
        "seo",
        "sem",
        "growth manager"
    ]),
    ("Recruiter", [
    "recruiter",
    "technical recruiter",
    "talent acquisition",
    "staffing"
    ]),


    ("HR Manager", [
    "human resources",
    "hr manager",
    "hrbp",
    "people operations",
    "people partner",
    "hr generalist"
    ]),

    ("Finance Analyst", [
        "finance analyst",
        "financial analyst",
        "strategic finance",
        "finance analytics",
        "corporate finance",
        "finance associate",
        "financial planning analyst",
        "fp&a analyst"
    ]),

    ("Accountant", [
        "accountant",
        "accounting",
        "controller",
        "auditor",
        "tax"
    ]),

    ("Legal Counsel", [
    "legal",
    "counsel",
    "compliance",
    "privacy"
    ]),



    ("Operations Manager", [
    "operations manager",
    "operations analyst",
    "office manager",
    "procurement",
    "logistics",
    "supply chain",
    "revops"
    ]),

    ("Solutions Engineer", [
    "solutions engineer",
    "solutions consultant",
    "sales engineer",
    "implementation engineer",
    "integration engineer",
    "consultant"
    ]),

    ("Technical Writer", [
    "technical writer",
    "documentation",
    "documentation engineer"
    ]),


    ("Analytics Engineer", [
        "analytics engineer",
        "advanced analytics",
        "analytics lead",
        "analytics manager",
        "business analytics",
        "analytics strategy"
    ]),

    
    ("Operations Manager", [
        "operations manager",
        "field operations",
        "business operations",
        "business operations lead",
        "operational planning",
        "capacity planning",
        "process strategy",
        "process optimization",
        "strategy and operations",
        "growth operations"
    ]),


    ("Operations Analyst", [
        "operations analyst",
        "forecasting analyst",
        "demand planning analyst",
        "workforce planning analyst",
        "capacity planning analyst"
    ]),




    ("Research Scientist", [
    "research scientist",
    "research engineer",
    "ml researcher",
    "ai researcher"
    ]),


    ("Executive Assistant", [
    "executive assistant",
    "executive coordinator",
    "administrative assistant"
    ]),
    
]

def load_taxonomy():
    with open(TAXONOMY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def map_by_keyword(title_lower):
    for canonical, keywords in KEYWORD_RULES:
        for kw in keywords:
            if kw in title_lower:
                return canonical
    return None


def map_by_fuzzy(title, taxonomy):
    matches = difflib.get_close_matches(title, taxonomy, n=1, cutoff=0.5)
    if matches:
        return matches[0]
    return "Other"


def map_title(raw_title, taxonomy):
    title_lower = raw_title.lower()
    result = map_by_keyword(title_lower)
    if result:
        return result, "keyword"
    result = map_by_fuzzy(raw_title, taxonomy)
    return result, "fuzzy"


def main():
    taxonomy = load_taxonomy()
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    raw_files = sorted(RAW_DIR.glob("*.json"))
    if not raw_files:
        print("No files found in data/raw/. Run scripts/fetch_jobs.py first (Stage 4).")
        return

    total_jobs = 0
    total_keyword = 0
    total_fuzzy = 0
    total_other = 0

    for raw_file in raw_files:
        with open(raw_file, "r", encoding="utf-8") as f:
            payload = json.load(f)

        jobs = payload.get("jobs", [])
        processed_jobs = []

        for job in jobs:
            raw_title = job.get("title", "")
            category, method = map_title(raw_title, taxonomy)

            total_jobs += 1
            if method == "keyword":
                total_keyword += 1
            else:
                total_fuzzy += 1
            if category == "Other":
                total_other += 1

            new_job = dict(job)
            new_job["raw_title"] = raw_title
            new_job["role_category"] = category
            processed_jobs.append(new_job)

        out_file = PROCESSED_DIR / raw_file.name
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump({"jobs": processed_jobs}, f, indent=2)

        print(f"{raw_file.stem:15s} -> {len(processed_jobs):4d} jobs mapped -> {out_file.relative_to(ROOT)}")

    print()
    print("=" * 50)
    print(f"Total jobs processed:        {total_jobs}")
    print(f"Mapped by keyword rule:      {total_keyword}")
    print(f"Mapped by fuzzy fallback:    {total_fuzzy}")
    print(f"Fell through to 'Other':     {total_other}")
    if total_jobs:
        print(f"'Other' rate:                {total_other / total_jobs * 100:.1f}%")
    print("=" * 50)
    print()
    print("Check a few titles below manually against their assigned category.")
    print("If 'Other' rate is high, or mappings look wrong, tell Claude some")
    print("example (raw_title -> role_category) pairs so the keyword rules")
    print("can be tuned.")


if __name__ == "__main__":
    main()
