export PROJECT_ID="wj-main"
export REGION="europe-central2"
export JOB_NAME="arxiv-digest"
export SCHED_SA="arxiv-digest-scheduler@${PROJECT_ID}.iam.gserviceaccount.com"
export SCHED_JOB="arxiv-digest-daily"
export PROJECT_NUMBER="383198106057"
export SCHEDULER_AGENT="service-${PROJECT_NUMBER}@gcp-sa-cloudscheduler.iam.gserviceaccount.com"
export JOB_SA="arxiv-digest-runner@wj-main.iam.gserviceaccount.com"


gsutil mb -l europe-central2 gs://arxiv-digest-data
gsutil versioning set on gs://arxiv-digest-data
gsutil iam ch serviceAccount:$JOB_SA:objectAdmin gs://arxiv-digest-data