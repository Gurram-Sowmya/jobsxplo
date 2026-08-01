"""
Jobxplo — Stage 5: role taxonomy mapping.

Reads every raw company file in data/raw/*.json (from Stage 4) and
adds a `role_category` field to each job, mapped from the messy
`raw_title` into one of the fixed categories in data/role_taxonomy.json.

IMPORTANT: every canonical name used on the left side of KEYWORD_RULES
below MUST exist in data/role_taxonomy.json. The frontend filter dropdown
is built from that file - a role_category that isn't in the taxonomy is
a job the user can never find by filtering, even though it's in the data.

Two-step mapping, cheapest first:
  1. Keyword rules   - if the title contains an obvious keyword, map it
                       directly. Free, fast, handles most titles.
  2. Fuzzy fallback   - for titles that don't match any keyword rule,
                       use difflib to find the closest canonical role
                       by text similarity, restricted to the taxonomy list.

This does NOT overwrite the raw title anywhere - `raw_title` is kept
untouched and always shown to the user later. `role_category` is only
used for filtering.

Usage:
    python3 scripts/map_roles.py
"""

import json
import difflib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
TAXONOMY_FILE = ROOT / "data" / "role_taxonomy.json"

# Step 1: keyword rules.
# Order matters - more specific keywords should come before general ones,
# and the FIRST matching rule wins (map_by_keyword returns immediately).
# Every canonical name here must exist in data/role_taxonomy.json -
# see the self-check in main() which verifies this on every run.
KEYWORD_RULES = [
    ("Site Reliability Engineer", ["site reliability", "sre", "production engineer", "reliability engineer", "performance engineer", "performance software engineer", "performance optimization engineer", "performance testing engineer", "application performance engineer", "systems performance engineer", "software reliability engineer", "service reliability engineer", "production reliability engineer", "site reliability engineer"]),
    ("DevOps Engineer", ["devops", "dev ops", "release engineer", "build engineer", "ci/cd", "deployment engineer", "automation engineer", "systems engineer", "system engineer", "systems software engineer", "system integration engineer", "systems development engineer", "computer systems engineer", "technical systems engineer", "network engineer", "network administrator", "network specialist", "network infrastructure engineer", "network operations engineer", "noc engineer", "network support engineer", "routing engineer", "switching engineer", "wireless network engineer", "platform engineer", "platform engineering", "developer platform engineer", "internal platform engineer", "cloud platform engineer", "platform infrastructure engineer", "developer experience engineer", "devex engineer", "developer productivity engineer", "kubernetes platform engineer", "container platform engineer", "infrastructure platform engineer", "infrastructure engineer", "infra engineer", "cloud infrastructure engineer", "infrastructure developer", "systems infrastructure engineer", "datacenter engineer", "server infrastructure engineer", "production infrastructure engineer", "it infrastructure engineer", "infrastructure operations engineer", "release management engineer", "software release engineer", "release automation engineer", "ci/cd engineer", "continuous delivery engineer", "continuous deployment engineer", "build and release engineer", "software build engineer", "compilation engineer", "build automation engineer", "developer tools engineer", "automation software engineer", "test automation engineer", "process automation engineer", "workflow automation engineer", "rpa engineer", "automation developer"]),
    ("Machine Learning Engineer", ["machine learning", "ml engineer", "mle", "ai engineer", "artificial intelligence", "genai", "generative ai", "llm", "computer vision", "nlp", "deep learning", "prompt engineer", "ai/ml researcher", "ml researcher", "artificial intelligence engineer", "artificial intelligence developer", "ai developer", "ai software engineer", "machine intelligence engineer", "intelligent systems engineer", "applied ai engineer", "ai solutions engineer", "generative ai engineer", "genai engineer", "gen ai engineer", "genai developer", "llm engineer", "llm developer", "large language model engineer", "large language model developer", "foundation model engineer", "ai application engineer", "rag engineer", "retrieval augmented generation engineer", "prompt engineering with llms", "llm application developer", "ai prompt engineer", "llm prompt engineer", "prompt designer", "prompt specialist", "prompt developer", "generative ai prompt engineer", "nlp engineer", "natural language processing engineer", "natural language processing", "nlp developer", "nlp scientist", "language model engineer", "computational linguist", "text analytics engineer", "speech nlp engineer", "conversational ai engineer", "chatbot engineer", "computer vision engineer", "cv engineer", "vision engineer", "computer vision developer", "image processing engineer", "image recognition engineer", "deep learning vision engineer", "opencv engineer", "autonomous vision engineer"]),
    ("Data Scientist", ["data scientist", "data science", "decision scientist", "quantitative analyst"]),
    ("Data Engineer", ["data engineer", "data engineering", "big data", "etl", "spark", "hadoop", "airflow", "analytics engineer", "data platform", "data infrastructure", "data architect", "database engineer", "database administrator", "dba", "big data engineer", "big data developer", "spark engineer", "hadoop engineer", "hadoop developer", "apache spark engineer", "spark developer", "big data analytics engineer", "distributed systems engineer", "data processing engineer", "data platform engineer", "mapreduce developer", "hive developer", "hbase developer", "kafka engineer", "etl developer", "etl engineer", "etl programmer", "data integration developer", "data pipeline developer", "data pipeline engineer", "batch processing developer", "informatica developer", "ssis developer", "talend developer", "ab initio developer", "data warehouse developer", "database developer", "database software engineer", "sql engineer", "database specialist", "database architect", "database reliability engineer", "database performance engineer", "database admin", "sql dba", "oracle dba", "mysql dba", "postgresql dba", "database operations engineer", "database support engineer", "database manager", "enterprise data architect", "cloud data architect", "big data architect", "data solutions architect", "data warehouse architect", "data platform architect", "information architect", "data quality engineer", "data quality analyst", "data validation engineer", "data testing engineer", "data integrity engineer", "data governance engineer", "data accuracy analyst", "data reliability engineer", "data governance", "data governance analyst", "data steward", "data management", "master data management", "mdm", "metadata management", "data compliance", "data policy analyst", "information governance", "databricks"]),
    ("Data Analyst", ["data analyst", "business intelligence", "bi developer", "bi engineer", "power bi", "tableau", "reporting analyst", "report analyst", "advanced analytics", "analytics analyst", "analytics lead", "analytics manager", "analytics engineer", "data analytics engineer", "analytics developer", "business analytics engineer", "dbt engineer", "dbt developer", "modern analytics engineer", "metrics engineer", "business intelligence engineer", "business intelligence developer", "bi analyst", "business intelligence analyst", "reporting engineer", "reporting developer", "dashboard engineer", "insights engineer", "power bi developer", "powerbi developer", "tableau developer", "tableau engineer", "qlik developer", "looker developer", "dashboard developer", "report developer", "business analytics", "analytics strategy"]),
    ("Cloud Engineer", ["cloud engineer", "cloud architect", "solutions architect", "solution architect", "cloud infrastructure", "aws solutions", "azure solutions", "gcp cloud", "cloud solutions architect", "cloud solution architect", "enterprise cloud architect", "cloud infrastructure architect", "aws solutions architect", "azure solutions architect", "gcp cloud architect", "cloud consultant architect", "aws", "azure", "gcp"]),
    ("Security Engineer", ["security engineer", "security analyst", "cyber security", "cybersecurity", "application security", "appsec", "infosec", "soc analyst", "penetration tester", "pentester", "ethical hacker", "iam engineer", "cloud security", "fraud intelligence", "fraud analyst", "trust and safety", "cyber security engineer", "cybersecurity engineer", "information security engineer", "infosec engineer", "security engineering", "security infrastructure engineer", "network security engineer", "application security engineer", "security operations engineer", "security operations center analyst", "security operations analyst", "soc engineer", "soc specialist", "cyber security analyst", "threat monitoring analyst", "incident monitoring analyst", "security monitoring analyst", "siem analyst", "information security analyst", "infosec analyst", "cybersecurity analyst", "threat analyst", "vulnerability analyst", "risk analyst", "security assessment analystfraud intelligence", "penetration testing", "pen tester", "offensive security engineer", "offensive security analyst", "red team engineer", "red team operator", "security researcher", "vulnerability researcher", "identity and access management", "identity access management engineer", "identity engineer", "access management engineer", "identity security engineer", "privileged access management engineer", "pam engineer", "okta engineer", "azure ad engineer", "entra id engineer", "cloud security engineer", "cloud security specialist", "cloud security analyst", "cloud cybersecurity engineer", "aws security engineer", "azure security engineer", "gcp security engineer", "cloud infrastructure security engineer", "cloud compliance engineer", "cloud security architect", "privacy engineer", "data privacy engineer", "privacy analyst", "privacy specialist", "privacy technology engineer", "privacy by design engineer", "information privacy engineer"]),
    ("QA Engineer", ["qa engineer", "quality assurance", "test engineer", "sdet", "automation tester", "automation test engineer", "manual tester", "performance tester", "test automation", "test automation engineer", "qa automation engineer", "automation qa engineer", "automated testing engineer", "selenium tester", "automation engineer qa", "software development engineer in test", "test automation developer", "manual testing", "manual qa tester", "manual qa engineer", "quality analyst", "software tester", "test analyst", "functional tester", "functional testing engineer", "load tester", "performance testing engineer", "performance test engineer", "load testing engineer", "stress tester", "stress testing engineer", "jmeter tester", "performance engineer", "qa"]),
    ("Mobile Engineer", ["ios engineer", "ios developer", "android engineer", "android developer", "mobile engineer", "mobile developer", "swift developer", "kotlin developer", "flutter developer", "react native", "flutter engineer", "flutter mobile developer", "dart developer", "dart engineer", "react native developer", "react native engineer", "react native mobile developer", "ios software engineer", "swift engineer", "objective-c developer", "objective c developer", "iphone developer", "ipad developer", "android software engineer", "kotlin engineer", "android application developer", "android app developer", "swift", "kotlin", "flutter"]),
    ("Frontend Engineer", ["frontend", "front-end", "front end engineer", "ui engineer", "react developer", "angular developer", "vue developer", "react engineer", "reactjs developer", "react.js developer", "react frontend developer", "react software engineer", "next.js developer", "nextjs developer", "angular engineer", "angularjs developer", "angular frontend developer", "typescript angular developer", "vue.js developer", "vuejs developer", "vue engineer", "vue frontend developer", "nuxt developer", "nuxt.js developer", "front end", "web engineer", "frontend developer"]),
    ("Backend Engineer", ["backend", "back-end", "back end engineer", "api engineer", "server engineer", "python developer", "python engineer", "python software engineer", "python backend developer", "python backend engineer", "python programmer", "python application developer", "python web developer", "django developer", "flask developer", "fastapi developer", "python api developer", "java developer", "java engineer", "java software engineer", "java backend developer", "java backend engineer", "java application developer", "j2ee developer", "jee developer", "spring developer", "spring boot developer", "java microservices developer", "c++ developer", "c++ engineer", "cpp developer", "cpp engineer", "c plus plus developer", "c++ software engineer", "c++ programmer", "embedded c++ developer", "c# developer", "c# engineer", "c sharp developer", "csharp developer", "c# software engineer", "dotnet c# developer", ".net developer", "dotnet developer", ".net engineer", "dot net developer", "asp.net developer", "asp.net core developer", ".net core developer", "c# .net developer", "microsoft .net developer", "golang", "go developer", "go engineer", "golang developer", "golang engineer", "go software engineer", "go backend developer", "rust developer", "rust engineer", "rust software engineer", "rust programmer", "systems rust developer", "php developer", "php engineer", "php software developer", "php web developer", "laravel developer", "symfony developer", "wordpress developer", "wordpress php developer", "ruby developer", "ruby engineer", "ruby on rails", "rails developer", "ror developer", "ruby software engineer", "nodejs", "node.js", "node developer", "node js developer", "node.js developer", "node backend developer", "nodejs engineer", "express.js developer", "express developer", "back end", "backend developer"]),
    ("Full Stack Engineer", ["full stack", "fullstack", "full stack developer", "full stack engineer"]),
    ("Engineering Manager", ["engineering manager", "eng manager", "software engineering manager", "development manager", "director of engineering", "engineering director", "vp engineering", "vice president engineering", "technical engineering manager", "software development manager", "chief technology officer", "cto", "chief technical officer", "technology officer", "vice president of engineering", "vp of engineering", "engineering vice president", "director software engineering", "director of software engineering", "software engineering director"]),
    ("Software Engineer", ["software engineer", "software developer", "swe", "application engineer", "applications engineer", "platform engineer", "infrastructure engineer", "systems engineer", "system engineer", "embedded engineer", "embedded software", "firmware engineer", "firmware developer", "python developer", "java developer", "golang", "go developer", "c++ developer", "c# developer", ".net developer", "dotnet developer", "php developer", "laravel developer", "ruby developer", "rails developer", "node developer", "node.js", "nodejs", "member of technical staff", "embedded software engineer", "embedded developer", "embedded systems engineer", "embedded systems developer", "microcontroller engineer", "mcu engineer", "rtos engineer", "firmware software engineer", "embedded firmware engineer", "device firmware engineer", "low level software engineer", "bios engineer", "bootloader engineer", "developer", "react developer", "angular developer", "vue developer", "flutter developer", "react native", "ios developer", "android developer", "swift developer", "kotlin developer", "staff software engineer", "principal software engineer", "lead software engineer", "senior software engineer", "software engineer i", "software engineer ii", "software engineer iii", "software engineer iv", "mts", "engineer, software"]),
    ("Solutions Engineer", ["solutions engineer", "sales engineer", "solutions consultant", "implementation engineer", "integration engineer", "technical consultant", "pre sales engineer", "presales engineer", "technical solutions engineer", "customer solutions engineer", "integration developer", "systems integration engineer", "api integration engineer", "software integration engineer", "middleware engineer", "pre-sales engineer", "technical sales engineer", "solution consultant", "consultant", "advisor", "consulting analyst", "business consultant", "business advisor", "management consultant", "strategy consultant", "business transformation consultant", "business process consultant", "solutions advisor", "technical solutions consultant", "implementation consultant", "pre sales consultant", "presales consultant", "technology consultant", "it consultant", "software consultant", "technical advisor"]),
    ("Support Engineer", ["support engineer", "technical support", "customer support engineer", "technical account manager", " tam ", "application support engineer", "technical support engineer", "production support engineer", "software support engineer", "technical support specialist", "support specialist", "application engineer", "applications engineer", "application software engineer", "application development engineer", "customer support", "customer service", "customer support specialist", "customer service representative", "customer care representative", "client support", "customer experience associate", "cx associate", "tech support engineer", "product support engineer", "it support engineer", "tam"]),
    ("Product Designer", ["product designer", "interaction designer", "visual designer"]),
    ("UI/UX Designer", ["ui designer", "ux designer", "ui/ux", "ux/ui", "graphic designer", "ux researcher", "user interface designer", "interface designer", "ui design specialist", "ui visual designer", "user experience designer", "ux specialist", "experience designer", "ux design specialist", "visual graphic designer", "creative graphic designer", "brand graphic designer", "graphic design specialist", "visual designer", "visual design specialist", "digital visual designer", "brand designer", "creative designer", "user experience researcher", "user researcher", "design researcher", "customer experience researcher", "interaction designer", "interaction design specialist", "product interaction designer", "human computer interaction designer", "hci designer"]),
    ("Product Manager", ["product manager", "technical product manager", "group product manager", "associate product manager", "product owner", "pm,", "technical pm", "tpm", "software product manager", "engineering product manager", "platform product manager", "technical product owner", "scrum product owner", "agile product owner", "product lead", "product platform manager", "pm"]),
    ("Program Manager", ["program manager", "technical program manager", "tpm", "engineering program manager", "technical program management", "technical project manager"]),
    ("Project Manager", ["project manager", "delivery manager", "scrum master"]),
    ("Business Analyst", ["business analyst", "business systems analyst", "functional analyst"]),
    ("Account Executive", ["account executive", "accounts associate", "enterprise account executive", "account manager", "enterprise accounts", "enterprise account", "account associate", "strategic accounts", "key accounts"]),
    ("Sales Development Representative", ["sales development", "sdr", "business development representative", "business development rep", "bdr", "sales development representative", "lead generation representative"]),
    ("Sales Executive", ["sales executive", "sales manager", "inside sales", "enterprise sales", "business development manager", "account manager", "sales lead", "sales director", "regional sales manager", "territory sales manager", "sales supervisor", "business development executive", "bd manager", "growth business manager", "partnership manager", "inside sales representative", "inside sales executive", "inside sales associate", "remote sales representative", "enterprise account executive", "enterprise sales manager", "strategic sales manager", "b2b enterprise sales", "business development"]),
    ("Customer Success Manager", ["customer success", "customer experience associate", "cx associate", "customer success engineer", "technical customer success engineer", "customer success technical engineer", "customer success specialist", "customer success technical specialist", "customer solutions engineer", "customer experience"]),
    ("Marketing Manager", ["marketing manager", "digital marketing", "brand manager", "marketing lead", "social media manager", "email marketing", "digital marketing specialist", "digital marketing executive", "online marketing specialist", "internet marketing specialist", "digital marketing manager", "email marketing specialist", "email marketing manager", "crm marketing specialist", "lifecycle marketing specialist", "marketing automation specialist", "brand marketing manager", "brand strategist", "brand specialist", "product marketing manager", "brand executive"]),
    ("Content Marketing", ["content marketing", "content writer", "copywriter", "seo specialist", "seo analyst", "seo manager", "search engine optimization", "organic search specialist", "seo strategist", "social media manager", "social media specialist", "social media strategist", "social media executive", "community manager", "social media coordinator", "technical writer"]),
    ("Growth Marketing", ["growth marketing", "performance marketing", "seo specialist", "sem specialist", "growth manager", "search engine marketing specialist", "paid search specialist", "ppc specialist", "google ads specialist", "paid media specialist", "performance marketing specialist", "growth marketing specialist", "paid marketing specialist", "digital performance marketer", "conversion rate optimization specialist", "cro specialist", "seo", "sem"]),
    ("Recruiter", ["recruiter", "technical recruiter", "talent acquisition", "staffing", "recruiting"]),
    ("HR Manager", ["human resources", "hr manager", "hrbp", "people operations", "people ops", "people partner", "hr generalist", "employee experience", "workforce operations", "human resources generalist", "hr specialist", "hr associate", "people specialist", "employee relations specialist", "people operations specialist", "people operations manager", "employee experience specialist", "recruiting systems", "talent operations", "workforce operationsemployee success"]),
    ("Finance Analyst", ["finance analyst", "financial analyst", "strategic finance", "finance analytics", "corporate finance", "fp&a", "investment analyst", "equity analyst", "research analyst", "financial investment analyst", "portfolio analyst", "investment associate", "finance associate", "financial planning analyst", "fp&a analyst"]),
    ("Accountant", ["accountant", "accounting", "controller", "auditor", "tax consultant", "tax analyst", "financial controller", "finance controller", "financial control manager", "corporate controller", "accounting controller", "internal auditor", "external auditor", "audit analyst", "audit associate", "financial auditor", "compliance auditor", "tax advisor", "tax associate", "tax specialist", "corporate tax consultant", "tax"]),
    ("Legal Counsel", ["legal", "counsel", "compliance officer", "compliance analyst", "privacy engineer", "public policy", "regulatory policy", "policy analyst", "policy economist", "compliance specialist", "regulatory compliance officer", "risk compliance analyst", "governance compliance specialistpublic policy", "compliance", "privacy"]),
    ("Operations Manager", ["operations manager", "ops manager", "office manager", "procurement", "logistics", "supply chain", "revops", "field operations", "business operations", "operational planning", "capacity planning", "process strategy", "process optimization", "strategy and operations", "growth operations", "office administrator", "administrative manager", "workplace manager", "office operations manager", "facility coordinator", "administrative coordinator", "supply chain manager", "supply chain specialist", "supply chain analyst", "supply chain lead", "supply chain operations manager", "logistics and supply chain manager", "supply planning manager", "procurement manager", "procurement specialist", "procurement analyst", "purchasing manager", "strategic sourcing manager", "sourcing specialist", "vendor management specialist", "logistics manager", "logistics specialist", "logistics analyst", "logistics coordinator", "transportation manager", "warehouse operations manager", "distribution manager", "chief operating officer", "coo", "operations officer", "operations analyst", "business operations lead"]),
    ("Operations Analyst", ["operations analyst", "forecasting analyst", "demand planning analyst", "workforce planning analyst", "business operations analyst", "ops analyst", "operations associate", "process analyst", "operational analyst", "business process analyst", "operations specialist", "capacity planning analyst"]),
    ("Technical Writer", ["technical writer", "documentation engineer", "documentation specialist", "technical documentation engineer", "documentation developer", "developer documentation engineer", "api documentation engineer", "documentation"]),
    ("Research Scientist", ["research scientist", "research engineer", "ai researcher", "ml researcher", "machine learning researcher", "deep learning researcher", "computer science researcher", "applied scientist", "research scientist ai", "research scientist machine learning"]),
    ("Executive Assistant", ["executive assistant", "executive coordinator", "administrative assistant", "personal assistant", "executive secretary", "chief of staff assistant"]),
]




def load_taxonomy():
    with open(TAXONOMY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def check_rules_match_taxonomy(taxonomy):
    """Fail loudly if a keyword rule points at a category the taxonomy
    doesn't have - this is exactly the bug that silently broke filtering."""
    taxonomy_set = set(taxonomy)
    bad = [canonical for canonical, _ in KEYWORD_RULES if canonical not in taxonomy_set]
    if bad:
        print("ERROR: these KEYWORD_RULES categories are not in role_taxonomy.json:")
        for b in bad:
            print("  -", b)
        raise SystemExit(1)


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
    check_rules_match_taxonomy(taxonomy)
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


if __name__ == "__main__":
    main()
