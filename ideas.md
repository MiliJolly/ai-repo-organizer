# ideas.md
# Dumping ground for feature ideas, half-baked thoughts, things to revisit
# Not a backlog. Just vibes.
# - Dev & Sarah

---

## ML / AI Ideas

- **LLM-powered churn explanations**: Instead of just a probability, generate a
  human-readable explanation: "This customer is at risk because they haven't
  purchased in 6 months and have 4 open support tickets." Could use GPT-4o or
  a fine-tuned Llama. Jake would love this for the CS team.

- **Real-time scoring**: right now predictions run in batch. Would be cool to
  score customers the moment they interact (API call, email open, etc.) and
  update the dashboard live. Needs a proper streaming pipeline - Kafka? Flink?
  Probably overkill for now.

- **Multi-touch attribution**: which marketing touchpoints actually lead to
  upsells? We have email_opens but not clicks, ad impressions, etc. Need to
  talk to marketing about data access.

- **Next Best Action (NBA)**: instead of just "recommend a product", recommend
  an action: email a discount, schedule a call, offer a free training session.
  Needs reward model / RL - very ambitious, save for v3.

- **Segment drift detection**: automatically alert when a cluster's average
  RFM scores change significantly week-over-week. Could use PSI (Population
  Stability Index) or KL divergence. Sarah has done this before at prev company.

- **A/B test framework for recommendations**: send different rec strategies to
  random customer subsets and measure conversion. No instrumentation yet.

---

## Product / UX Ideas

- Heatmap of customer locations on a world map (if we had geo data - don't yet)

- Slack bot integration: "hey @customerai who are my top at-risk VIPs this week?"
  Marcus thought this was cool. Jake said it's scope creep.

- Customer health score (single 0-100 number combining churn risk, CLV trend,
  support tickets, engagement). Simpler than showing 5 separate metrics.
  Could replace the separate KPI cards.

- Mobile-responsive dashboard. Right now it's desktop only. Lisa checks it on
  her phone and complains every week.

- Dark/light mode toggle. Marcus added dark mode CSS variables so it should
  be straightforward... but who has time.

- Bulk actions in the table: select multiple customers → add to campaign,
  export, change segment manually.

---

## Infrastructure / Tech Debt

- Docker Compose setup so new devs don't have to fight with venv and path issues.
  Dev keeps saying he'll do it. Maybe this weekend.

- CI/CD: currently just manually deploying. GitHub Actions for at minimum:
  - lint + test on PR
  - auto-deploy to staging on merge to main
  (Dev to set up, needs AWS creds from Jake)

- Proper secret management - stop using env vars for DB password and API key.
  AWS Secrets Manager or HashiCorp Vault. Jake said "after funding round" 🙄

- The repo is a mess. Agreed in 2024-11-07 meeting to "clean it up."
  Someone needs to create a proper folder structure:
    src/backend/, src/frontend/, ml/, data/, scripts/, docs/
  Dev volunteered Sarah. Sarah nominated Marcus. Marcus ignored the Slack message.

- Switch from CSV files to a real database. Everyone agrees. Nobody has done it.

---

## Random / Crazy Ideas (do not take seriously)

- "Predict future revenue" - like, total company ARR prediction. Way out of scope.
- Customer personality types based on purchase behavior (Myers-Briggs for B2B lol)
- Gamification - give CSMs points for saving at-risk customers
- Auto-generated weekly PDF report emailed to leadership
  (Lisa wants this, Jake said "build it", Dev said "fine, 2 weeks")
