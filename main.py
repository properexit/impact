from concurrent.futures import ThreadPoolExecutor

# ✅ Import FUNCTIONS, not modules
from agents.planner import planner_agent
from agents.data_agent import data_agent
from agents.geo_agent import geo_agent
from agents.environment_agent import environment_agent
from agents.technical_agent import technical_agent
from agents.report_agent import report_agent


def run_pipeline(lat, lon):
    print("\n🧠 Planner Agent...")
    plan = planner_agent(lat, lon)
    print(plan)

    print("\n📥 Data Agent...")
    data = data_agent(lat, lon)

    print("\n🗺 Geo Agent...")
    geo = geo_agent(lat, lon, data)
    print(geo)

    print("\n⚡ Running Domain Agents in Parallel...")

    with ThreadPoolExecutor() as executor:
        env_future = executor.submit(environment_agent, geo)
        tech_future = executor.submit(technical_agent, geo)

        env_result = env_future.result()
        tech_result = tech_future.result()

    combined = {**env_result, **tech_result}
    print("\n📊 Combined Insights:")
    print(combined)

    print("\n📝 Report Agent...")
    report = report_agent(lat, lon, combined)

    print("\n📄 FINAL REPORT:\n")
    print(report)


if __name__ == "__main__":
    print("🚀 Starting Due Diligence Pipeline...")
    run_pipeline(52.52, 13.405)