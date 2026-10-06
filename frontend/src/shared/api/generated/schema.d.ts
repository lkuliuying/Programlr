// 从本工程 ../contracts/openapi.yaml 自动生成，请勿手工修改。
export type ClientOptions = {
  baseUrl: `${string}://${string}` | (string & {});
};
export type ActionEnum = 'confirm' | 'exclude' | 'reset';
export type AlgorithmEnum = 'bfs' | 'dfs';
export type Analysis = {
  readonly id: string;
  readonly job_id: string;
  readonly snapshot_id: string;
  readonly root_urlconf: string;
  readonly rule_version: string;
  coverage: Coverage;
  frontend: FrontendSummary | null;
  readonly created_at: string;
  readonly source_scan_id: string | null;
};
export type AnalysisInputRequest = {
  root_urlconf: string;
};
export type AnalysisVersion = {
  analysis_id: string;
  snapshot_id: string;
  root_urlconf: string;
  rule_version: string;
  graph_version: string | null;
  frontend_rule_version: string | null;
  association_rule_version: string | null;
};
export type ApplicabilityEnum = 'unchanged' | 'review' | 'deleted' | 'unknown';
export type AttemptFeedback = {
  expected_answer: unknown;
  explanation: string;
  source_refs: Array<SourceRef>;
};
export type AttemptInputRequest = {
  snapshot_id: string;
  exercise_id: string;
  exercise_version: string;
  analysis_id: string;
  endpoint_index: number;
  answer: unknown;
  hint_used: boolean;
  previous_attempt_id?: string | null;
};
export type AttemptReview = {
  readonly id: string;
  attempt_id: string;
  judgement: JudgementEnum;
  readonly note: string;
  readonly created_at: string;
};
export type AttemptReviewPage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Array<AttemptReview>;
};
export type CandidateStatusEnum = 'selected' | 'needs_root' | 'no_root';
export type CaseIdEnum = 'first' | 'second';
export type ChangedFieldsEnum =
  'action' | 'view' | 'serializer' | 'model' | 'relations';
export type ComparabilityEnum = 'comparable' | 'files_only' | 'incomparable';
export type ComparisonFile = {
  id: string;
  file_path: string;
  change_type: ComparisonFileChangeEnum;
  base_ref: SourceRef | null;
  target_ref: SourceRef | null;
  base_sha256: string | null;
  target_sha256: string | null;
};
export type ComparisonFileChangeEnum =
  'added' | 'deleted' | 'modified' | 'unchanged';
export type ComparisonFileDetail = {
  id: string;
  file_path: string;
  change_type: ComparisonFileChangeEnum;
  base_ref: SourceRef | null;
  target_ref: SourceRef | null;
  base_sha256: string | null;
  target_sha256: string | null;
  diff: string;
  base_ranges: Array<SourceRef>;
  target_ranges: Array<SourceRef>;
};
export type ComparisonFilePage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Array<ComparisonFile>;
};
export type ComparisonHistory = {
  readonly id: string;
  readonly project_id: string;
  readonly job_id: string;
  job_status: StatusEnum;
  readonly base_snapshot_id: string;
  readonly target_snapshot_id: string;
  readonly base_analysis_id: string | null;
  readonly target_analysis_id: string | null;
  summary: FileSummary | null;
  readonly created_at: string;
};
export type ComparisonHistoryPage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Array<ComparisonHistory>;
};
export type ComparisonImpact = {
  comparison_id: string;
  change_id: string | null;
  include_candidates: boolean;
  base: ImpactSide;
  target: ImpactSide;
  limitations: Array<string>;
};
export type ComparisonInputRequest = {
  base_snapshot_id: string;
  target_snapshot_id: string;
  base_analysis_id?: string | null;
  target_analysis_id?: string | null;
};
export type ConsentInputRequest = {
  accepted: boolean;
};
export type ContextConsent = {
  readonly id: string;
  preview_id: string;
  readonly created_at: string;
};
export type ContextPreview = {
  id: string;
  analysis_id: string;
  snapshot_id: string;
  endpoint_index: number;
  payload_digest: string;
  configuration: ModelTarget;
  template_version: string;
  messages: Array<PreviewMessage>;
  snippets: Array<PreviewSnippet>;
  excluded_snippets: Array<string>;
  nodes: Array<PreviewNode>;
  omissions: Array<string>;
  context_bytes: number;
  knowledge_cards?: Array<PreviewKnowledgeCard>;
  created_at: string;
};
export type Coverage = {
  python_files: number;
  parsed_files: number;
  syntax_failed_files: number;
  skipped_files: number;
  endpoint_count: number;
  diagnostic_count: number;
  complete: boolean;
  limitations: Array<string>;
};
export type Csrf = {
  csrf_token: string;
};
export type CurriculumDefinition = {
  slug: string;
  version: string;
  title: string;
  example_version: string;
  review_note: string;
  nodes: Array<CurriculumNode>;
  edges: Array<PrerequisiteEdge>;
  goals: {
    [key: string]: Array<string>;
  };
};
export type CurriculumNode = {
  slug: string;
  card_version: string;
};
export type CurriculumPage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Array<KnowledgeCurriculum>;
};
export type CurriculumProgress = {
  curriculum_id: string;
  version: string;
  completed_count: number;
  total_count: number;
  cards: Array<CurriculumProgressCard>;
};
export type CurriculumProgressCard = {
  card_id: string;
  slug: string;
  version: string;
  title: string;
  completed: boolean;
};
export type DecisionEnum = 'confirmed' | 'excluded' | 'undecided';
export type DeletionPreview = {
  target_type: TargetTypeEnum;
  target_id: string;
  project_id: string;
  object_name: string;
  scope: DeletionScope;
  confirmation_digest: string;
  can_delete: boolean;
  receiving: boolean;
  busy_jobs: Array<Job>;
};
export type DeletionScope = {
  snapshots: number;
  files: number;
  analyses: number;
  source_scans: number;
  explanations: number;
  attempts: number;
  lab_runs: number;
  comparisons: number;
};
export type Diagnostic = {
  code: string;
  message: string;
  severity: SeverityEnum;
  source_ref: SourceRef | null;
};
export type DiagnosticPage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Array<Diagnostic>;
};
export type DirectionEnum = 'undirected';
export type Endpoint = {
  readonly index: number;
  readonly frontend_available: boolean;
  readonly frontend_links: Array<FrontendLink>;
  method: MethodEnum;
  path: string;
  path_kind: PathKindEnum;
  action: string;
  view: Symbol | null;
  serializer: Symbol | null;
  model: Symbol | null;
  evidence: Array<Evidence>;
};
export type EndpointChange = {
  method: string;
  path: string;
  path_kind: PathKindEnum;
  change_type: SemanticChangeEnum;
  base_indices: Array<number>;
  target_indices: Array<number>;
  changed_fields: Array<ChangedFieldsEnum>;
  base_evidence: Array<Evidence>;
  target_evidence: Array<Evidence>;
};
export type EndpointPage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Array<Endpoint>;
};
export type Error = {
  code: string;
  message: string;
  details: {
    [key: string]: unknown;
  };
  request_id: string;
};
export type Evidence = {
  kind: KindEnum;
  rule: string;
  source_ref: SourceRef | null;
};
export type EvidenceKindEnum = 'language' | 'declaration' | 'usage';
export type Exercise = {
  readonly id: string;
  readonly slug: string;
  readonly version: string;
  readonly answer_version: string;
  example_version: string;
  kind: ExerciseKindEnum;
  readonly question: string;
  readonly hint: string;
  options: Array<ExerciseOption>;
  readonly review_note: string;
  readonly applicable: boolean;
  readonly applicability_reason: string;
};
export type ExerciseAttempt = {
  readonly id: string;
  exercise_id: string;
  exercise_version: string;
  answer_version: string;
  example_version: string;
  question: string;
  kind: string;
  snapshot_id: string;
  analysis_id: string;
  readonly endpoint_index: number;
  readonly answer: unknown;
  readonly hint_used: boolean;
  readonly correct: boolean;
  feedback: AttemptFeedback;
  readonly created_at: string;
  previous_attempt_id: string | null;
};
export type ExerciseAttemptPage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Array<ExerciseAttempt>;
};
export type ExerciseKindEnum =
  'flow_order' | 'error_prediction' | 'code_location';
export type ExerciseOption = {
  id: string;
  label: string;
};
export type ExercisePage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Array<Exercise>;
};
export type Explanation = {
  readonly id: string;
  job_id: string;
  preview_id: string;
  analysis_id: string;
  snapshot_id: string;
  endpoint_index: number;
  template_version: string;
  readonly model: string;
  usage: ModelUsage | null;
  content: ExplanationContent;
  readonly created_at: string;
};
export type ExplanationApplicability = {
  explanation_id: string;
  preview_id: string;
  analysis_id: string;
  endpoint_index: number;
  references: Array<ReferenceApplicability>;
  warning: string | null;
};
export type ExplanationClaim = {
  kind: ExplanationClaimKindEnum;
  text: string;
  source_refs: Array<SourceRef>;
};
export type ExplanationClaimKindEnum =
  'source_fact' | 'static_inference' | 'general_principle';
export type ExplanationContent = {
  purpose: Array<ExplanationClaim>;
  evidence: Array<ExplanationClaim>;
  mechanism: Array<ExplanationClaim>;
  knowledge: Array<ExplanationClaim>;
  verification: Array<ExplanationClaim>;
};
export type ExplanationInputRequest = {
  consent_id: string;
};
export type ExplanationPage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Array<Explanation>;
};
export type FileSummary = {
  added: number;
  deleted: number;
  modified: number;
  unchanged: number;
};
export type FolderInputRequest = {
  manifest: Blob | File;
  files: Array<Blob | File>;
};
export type FrontendCoverage = {
  source_files: number;
  parsed_files: number;
  syntax_failed_files: number;
  function_count: number;
  request_count: number;
  complete: boolean;
  limitations: Array<string>;
};
export type FrontendLink = {
  request_id: string;
  method: string | null;
  path: string | null;
  status: FrontendMatchStatusEnum;
  reason: string;
  source_ref: SourceRef;
  relation_review: RelationDecision | null;
};
export type FrontendMatchStatusEnum = 'confirmed' | 'candidate' | 'unmatched';
export type FrontendSummary = {
  protocol_version: string;
  rule_version: string;
  association_rule_version: string;
  coverage: FrontendCoverage;
  confirmed: number;
  candidate: number;
  unmatched: number;
};
export type Graph = {
  analysis_id: string;
  snapshot_id: string;
  rule_version: string;
  graph_version: string;
  root_node_id: string | null;
  endpoint_index: number | null;
  algorithm: AlgorithmEnum;
  nodes: Array<GraphNode>;
  edges: Array<GraphEdge>;
  readonly relation_reviews: Array<RelationDecision>;
  coverage: Coverage;
  diagnostics_url: string;
  total_nodes: number;
  total_edges: number;
  returned_nodes: number;
  returned_edges: number;
  truncated: boolean;
  truncation_reasons: Array<TruncationReasonsEnum>;
};
export type GraphEdge = {
  id: string;
  source_id: string;
  target_id: string;
  relation: RelationEnum;
  evidence: Array<Evidence>;
};
export type GraphEndpoint = {
  index: number;
  method: MethodEnum;
  path: string;
  path_kind: PathKindEnum;
  action: string;
  is_candidate: boolean;
};
export type GraphNode = {
  id: string;
  kind: GraphNodeKindEnum;
  name: string;
  source_ref: SourceRef | null;
  evidence: Array<Evidence>;
  endpoint: GraphEndpoint | null;
  request?: GraphRequest | null;
};
export type GraphNodeKindEnum =
  | 'endpoint'
  | 'view'
  | 'serializer'
  | 'model'
  | 'frontend_function'
  | 'frontend_request';
export type GraphRequest = {
  method: string | null;
  original_path: string | null;
  path: string | null;
  status: FrontendMatchStatusEnum;
  reason: string;
};
export type Impact = {
  analysis_id: string;
  snapshot_id: string;
  graph_version: string;
  rule_version: string;
  include_candidates: boolean;
  max_nodes: number;
  max_edges: number;
  starts: Array<string>;
  nodes: Array<GraphNode>;
  edges: Array<GraphEdge>;
  results: Array<ImpactResult>;
  relation_reviews: Array<RelationDecision>;
  visited_nodes: number;
  visited_edges: number;
  truncated: boolean;
  truncation_reasons: Array<string>;
  unmapped_files: Array<string>;
  uncovered_files: Array<string>;
  limitations: Array<string>;
  diagnostics: Array<Diagnostic>;
  diagnostics_url: string;
};
export type ImpactResult = {
  node: GraphNode;
  path_node_ids: Array<string>;
  path_edge_ids: Array<string>;
  via_candidate: boolean;
};
export type ImpactSide = {
  snapshot_id: string;
  analysis_id: string | null;
  available: boolean;
  reason: string | null;
  changed_files: Array<string>;
  impact: Impact | null;
};
export type ImportInputRequest = {
  archive: Blob | File;
};
export type ImportSummary = {
  entries: number;
  accepted: number;
  excluded: number;
  skipped: number;
  rejected: number;
  declared_bytes: number;
  extracted_bytes: number;
  reasons: {
    [key: string]: number;
  };
};
export type Job = {
  readonly id: string;
  readonly kind: string;
  readonly snapshot_id: string | null;
  status: StatusEnum;
  readonly stage: string;
  readonly progress: {
    [key: string]: number | null;
  } | null;
  readonly previous_job_id: string | null;
  readonly parent_job_id: string | null;
  readonly source_kind: string;
  readonly result_deleted_at: string | null;
  readonly result_deleted: boolean;
  readonly result_url: string | null;
  error: Error | null;
  readonly created_at: string;
  readonly updated_at: string;
};
export type JobPage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Array<Job>;
};
export type JudgementEnum = 'revisit' | 'practicing' | 'understood';
export type KindEnum = 'source_fact' | 'static_inference' | 'framework_rule';
export type KnowledgeCard = {
  readonly id: string;
  readonly slug: string;
  readonly version: string;
  readonly title: string;
  readonly body: string;
  readonly applicability: string;
  readonly review_note: string;
};
export type KnowledgeCardPage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Array<KnowledgeCard>;
};
export type KnowledgeCoverage = {
  python_files: number;
  parsed_files: number;
  syntax_failed_files: number;
  hit_count: number;
  package_count: number;
  complete: boolean;
  truncated: boolean;
};
export type KnowledgeCurriculum = {
  readonly id: string;
  readonly slug: string;
  readonly version: string;
  readonly title: string;
  definition: CurriculumDefinition;
  readonly content_digest: string;
};
export type KnowledgeHit = {
  concept_key: string;
  card_slug: string | null;
  card_version: string | null;
  rule_id: string;
  source_ref: SourceRef;
};
export type KnowledgeHitPage = {
  count: number;
  next: string | null;
  previous: string | null;
  scan_id: string;
  rule_version: string;
  results: Array<KnowledgeHit>;
};
export type KnowledgeHitPreview = {
  reason: string;
  source_ref: SourceRef;
};
export type KnowledgePackage = {
  name: string;
  kind: KnowledgePackageKindEnum;
  distribution: string | null;
};
export type KnowledgePackageKindEnum =
  'local' | 'stdlib' | 'third_party' | 'unknown';
export type Lab = {
  id: string;
  version: string;
  title: string;
  example_version: string;
  description: string;
  cases: Array<LabCase>;
  applicable: boolean;
  applicability_reason: string;
};
export type LabCase = {
  id: string;
  title: string;
  input: {
    [key: string]: string;
  };
};
export type LabCleanup = {
  status?: string;
  observation?: {
    [key: string]: unknown;
  } | null;
  error_code?: string | null;
};
export type LabInputRequest = {
  snapshot_id: string;
  analysis_id: string;
  endpoint_index: number;
  lab_version: string;
  predictions: PredictionsRequest;
};
export type LabObservation = {
  case_id: string;
  input: {
    [key: string]: string;
  };
  request_path: string;
  response: LabResponse;
  before_count: number;
  after_count: number | null;
  elapsed_ms: number;
  observed_at: string;
};
export type LabPage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Array<Lab>;
};
export type LabResponse = {
  status: number;
  body: {
    [key: string]: unknown;
  };
};
export type LabRun = {
  readonly id: string;
  job: Job;
  snapshot_id: string;
  analysis_id: string;
  readonly endpoint_index: number;
  definition: Lab;
  predictions: Predictions;
  observations: Array<LabObservation>;
  cleanup: LabCleanup;
  readonly created_at: string;
};
export type LabRunPage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Array<LabRun>;
};
export type LearningPath = {
  snapshot_id: string;
  analysis_id: string;
  endpoint_index: number;
  curriculum: KnowledgeCurriculum;
  goal: string;
  targets: Array<string>;
  order: Array<string>;
  steps: Array<KnowledgeCard>;
  applicable: boolean;
  applicability_reason: string;
};
export type MatchedKnowledgeCard = {
  concept_key: string;
  card: KnowledgeCard | null;
  mapped: boolean;
  hit_count: number;
  hits: Array<KnowledgeHitPreview>;
  package: KnowledgePackage | null;
};
export type MethodEnum =
  'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE' | 'HEAD' | 'OPTIONS' | 'TRACE';
export type ModelTarget = {
  base_url: string;
  model: string;
  timeout?: number;
  context_bytes?: number;
  output_tokens?: number;
  token_field?: string;
};
export type ModelUsage = {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
};
export type Notification = {
  job: Job;
  read: boolean;
};
export type NotificationPage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Array<Notification>;
  unread_count: number;
  as_of: string;
  read_through: string | null;
};
export type OperationLog = {
  readonly id: string;
  readonly display_id: number;
  readonly operation: string;
  readonly result: string;
  readonly request_id: string;
  readonly project_id: string | null;
  readonly project_name: string;
  readonly snapshot_id: string | null;
  readonly object_name: string;
  readonly source_kind: string;
  readonly job_id: string | null;
  job: Job | null;
  readonly error_code: string;
  readonly events: Array<{
    [key: string]: unknown;
  }>;
  readonly result_deleted: boolean;
  readonly started_at: string;
  readonly ended_at: string | null;
  readonly created_at: string;
  readonly updated_at: string;
  retry_action: RetryActionEnum;
  readonly retry_reason: string;
  readonly project_available: boolean;
};
export type OperationLogPage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Array<OperationLog>;
};
export type OperationStatistics = {
  as_of: string;
  count: number;
  failed_count: number;
  active_count: number;
  retryable_count: number;
  recent_success_rate: number | null;
  previous_success_rate: number | null;
  success_rate_change_pp: number | null;
  recent_window: OperationWindow;
  previous_window: OperationWindow;
  trend: Array<OperationTrend>;
};
export type OperationTrend = {
  start: string;
  end: string;
  count: number;
  failed_count: number;
};
export type OperationWindow = {
  start: string;
  end: string;
};
export type PatchedCurriculumProgressInputRequest = {
  completed: boolean;
};
export type PatchedNotificationReadInputRequest = {
  read: boolean;
};
export type PatchedNotificationReadStateInputRequest = {
  read_through: string;
};
export type PatchedSnapshotNameInputRequest = {
  name: string;
};
export type PathKindEnum = 'django_path' | 'router_regex';
export type Prediction = {
  status: number;
  writes: number;
};
export type PredictionRequest = {
  status: number;
  writes: number;
};
export type Predictions = {
  normal: Prediction;
  missing: Prediction;
  empty: Prediction;
  whitespace: Prediction;
};
export type PredictionsRequest = {
  normal: PredictionRequest;
  missing: PredictionRequest;
  empty: PredictionRequest;
  whitespace: PredictionRequest;
};
export type PrerequisiteEdge = {
  prerequisite: string;
  dependent: string;
};
export type PreviewInputRequest = {
  analysis_id: string;
  endpoint_index: number;
  node_ids?: Array<string>;
  excluded_snippets?: Array<string>;
};
export type PreviewKnowledgeCard = {
  card_id: string;
  slug: string;
  version: string;
  content_digest: string;
  title: string;
  body: string;
  source_refs: Array<SourceRef>;
};
export type PreviewMessage = {
  role: RoleEnum;
  content: string;
};
export type PreviewNode = {
  id: string;
  name: string;
  kind: string;
};
export type PreviewSnippet = {
  id: string;
  source_ref: SourceRef;
  sha256: string;
  content: string;
};
export type Project = {
  readonly id: string;
  readonly name: string;
  readonly created_at: string;
};
export type ProjectActivity = {
  active: Array<ProjectActivityItem>;
  recent: Array<ProjectActivityItem>;
};
export type ProjectActivityEvent = {
  at: string;
  result: string;
  stage: string;
  error_code: string;
};
export type ProjectActivityItem = {
  project: Project;
  snapshot: Snapshot | null;
  status: ProjectActivityItemStatusEnum;
  root_count: number | null;
  endpoint_count: number | null;
  stages: Array<ProjectActivityStage>;
};
export type ProjectActivityItemStatusEnum =
  | 'importing'
  | 'scanning'
  | 'needs_root'
  | 'no_root'
  | 'analyzing'
  | 'ready'
  | 'failed'
  | 'pending';
export type ProjectActivityStage = {
  kind: ProjectActivityStageKindEnum;
  job: Job;
  events: Array<ProjectActivityEvent>;
};
export type ProjectActivityStageKindEnum =
  'import' | 'source_scan' | 'analysis';
export type ProjectInputRequest = {
  name: string;
};
export type ProjectManagementPage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Array<ProjectSummary>;
  technologies: Array<string>;
};
export type ProjectPage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Array<Project>;
};
export type ProjectSummary = {
  project: Project;
  snapshot_count: number;
  latest_snapshot: Snapshot | null;
  last_imported_at: string | null;
  technologies: Array<ProjectTechnology>;
  root_count: number | null;
  root_path: string | null;
};
export type ProjectTechnology = {
  name: string;
  evidence_kind: EvidenceKindEnum;
};
export type ReferenceApplicability = {
  source_ref: SourceRef;
  target_ref: SourceRef | null;
  applicability: ApplicabilityEnum;
};
export type RelatedOperationLog = {
  readonly id: string;
  readonly display_id: number;
  readonly operation: string;
  readonly result: string;
  readonly request_id: string;
  readonly project_id: string | null;
  readonly project_name: string;
  readonly snapshot_id: string | null;
  readonly object_name: string;
  readonly source_kind: string;
  readonly job_id: string | null;
  job: Job | null;
  readonly error_code: string;
  readonly events: Array<{
    [key: string]: unknown;
  }>;
  readonly result_deleted: boolean;
  readonly started_at: string;
  readonly ended_at: string | null;
  readonly created_at: string;
  readonly updated_at: string;
  retry_action: RetryActionEnum;
  readonly retry_reason: string;
  readonly project_available: boolean;
  readonly relation: string;
};
export type RelatedOperationLogPage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Array<RelatedOperationLog>;
};
export type RelationChange = {
  relation: string;
  source_name: string;
  target_name: string;
  change_type: SemanticChangeEnum;
  base_edge_ids: Array<string>;
  target_edge_ids: Array<string>;
  base_evidence: Array<Evidence>;
  target_evidence: Array<Evidence>;
};
export type RelationDecision = {
  request_id: string;
  target_id: string;
  revision: number;
  decision: DecisionEnum;
};
export type RelationEnum =
  | 'route_view'
  | 'serializer_class'
  | 'meta_model'
  | 'direct_call'
  | 'contains_function'
  | 'contains_request'
  | 'callback_binding'
  | 'method_path_match'
  | 'candidate_match';
export type RelationReview = {
  readonly id: string;
  readonly analysis_id: string;
  readonly request_id: string;
  readonly target_id: string;
  action: ActionEnum;
  readonly revision: number;
  readonly created_at: string;
};
export type RelationReviewInputRequest = {
  request_id: string;
  target_id: string;
  action: ActionEnum;
  expected_revision: number;
};
export type RelationReviewPage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Array<RelationReview>;
  state: RelationReviewState;
};
export type RelationReviewResult = {
  record: RelationReview;
  state: RelationReviewState;
};
export type RelationReviewState = {
  analysis_id: string;
  request_id: string;
  revision: number;
  confirmed_target_id: string | null;
  excluded_target_ids: Array<string>;
};
export type RetryActionEnum =
  | 'none'
  | 'direct'
  | 'upload_zip'
  | 'select_folder'
  | 'reconfirm_explanation'
  | 'continue_cleanup';
export type ReviewInputRequest = {
  attempt_id: string;
  judgement: JudgementEnum;
  note?: string;
};
export type RoleEnum = 'system' | 'user';
export type RootCandidate = {
  file_path: string;
  module: string;
  reason: string;
  source_refs: Array<SourceRef>;
};
export type SemanticChangeEnum =
  'added' | 'deleted' | 'modified' | 'unchanged' | 'ambiguous';
export type SeverityEnum = 'warning';
export type SharedGraph = {
  analysis_id: string;
  snapshot_id: string;
  rule_version: string;
  graph_version: string;
  root_node_id: string | null;
  endpoint_index: number | null;
  algorithm: AlgorithmEnum;
  nodes: Array<GraphNode>;
  edges: Array<GraphEdge>;
  readonly relation_reviews: Array<RelationDecision>;
  coverage: Coverage;
  diagnostics_url: string;
  total_nodes: number;
  total_edges: number;
  returned_nodes: number;
  returned_edges: number;
  truncated: boolean;
  truncation_reasons: Array<TruncationReasonsEnum>;
  direction: DirectionEnum;
  scope: SharedGraphScopeEnum;
};
export type SharedGraphScopeEnum =
  'connected_shared_symbols' | 'all_shared_symbols';
export type Snapshot = {
  readonly id: string;
  readonly name: string;
  readonly project_id: string;
  readonly job_id: string;
  summary: ImportSummary;
  readonly source_extensions: Array<string>;
  readonly source_manifest_names: Array<string>;
  readonly preparation_status: string;
  readonly source_scan_id: string | null;
  readonly scan_job_id: string | null;
  readonly analysis_job_id: string | null;
  readonly analysis_id: string | null;
  readonly created_at: string;
};
export type SnapshotComparison = {
  id: string;
  project_id: string;
  job_id: string;
  base_snapshot_id: string;
  target_snapshot_id: string;
  base_analysis_id: string | null;
  target_analysis_id: string | null;
  comparison_version: string;
  created_at: string;
  summary: FileSummary;
  comparability: ComparabilityEnum;
  comparison_notes: Array<string>;
  base_version: AnalysisVersion | null;
  target_version: AnalysisVersion | null;
  interfaces: Array<EndpointChange>;
  relations: Array<RelationChange>;
  evidence: Array<ExplanationApplicability>;
};
export type SnapshotKnowledgePage = {
  count: number;
  next: string | null;
  previous: string | null;
  scan_id: string;
  rule_version: string;
  coverage: KnowledgeCoverage;
  diagnostics: Array<Diagnostic>;
  results: Array<MatchedKnowledgeCard>;
};
export type SnapshotPage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Array<Snapshot>;
};
export type SnapshotSearchPage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Array<SnapshotSearchResult>;
};
export type SnapshotSearchResult = {
  snapshot: Snapshot;
  project: Project;
};
export type SourceContent = {
  readonly id: string;
  readonly snapshot_id: string;
  readonly file_path: string;
  readonly sha256: string;
  readonly size_bytes: number;
  readonly line_count: number;
  readonly encoding: string;
  start_line: number;
  end_line: number;
  content: string;
};
export type SourceEvidence = {
  id: string;
  kind: SourceEvidenceKindEnum;
  label: string;
  source_ref: SourceRef;
  endpoint_index: number | null;
  node_id: string | null;
  concept_key: string | null;
};
export type SourceEvidenceKindEnum =
  'interface' | 'frontend' | 'relation' | 'knowledge';
export type SourceEvidencePage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Array<SourceEvidence>;
  snapshot_id: string;
  file_id: string;
  analysis_id: string | null;
  scan_id: string | null;
  scope: SourceEvidencePageScopeEnum;
};
export type SourceEvidencePageScopeEnum = 'persisted_source_evidence';
export type SourceFile = {
  readonly id: string;
  readonly snapshot_id: string;
  readonly file_path: string;
  readonly sha256: string;
  readonly size_bytes: number;
  readonly line_count: number;
  readonly encoding: string;
};
export type SourceFilePage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Array<SourceFile>;
};
export type SourceRef = {
  snapshot_id: string;
  file_path: string;
  start_line: number;
  end_line: number;
};
export type SourceScan = {
  id: string;
  snapshot_id: string;
  job_id: string;
  scan_version: string;
  candidate_status: CandidateStatusEnum;
  selected_root: string | null;
  root_candidates: Array<RootCandidate>;
  knowledge: unknown;
  diagnostics: unknown;
  created_at: string;
};
export type StatusEnum = 'queued' | 'running' | 'succeeded' | 'failed';
export type Symbol = {
  name: string;
  source_ref: SourceRef;
};
export type SystemCheck = {
  readonly id: string;
  job_id: string;
  readonly check_version: string;
  readonly database: string;
  readonly queue: string;
  readonly worker: string;
  readonly completed_at: string;
};
export type SystemCleanup = {
  status?: SystemCleanupStatusEnum;
  error_code?: string | null;
};
export type SystemCleanupStatusEnum = 'pending' | 'completed' | 'unconfirmed';
export type SystemLab = {
  id: string;
  version: string;
  title: string;
  example_version: string;
  program_digest: string;
  description: string;
  cases: Array<SystemLabCase>;
  applicable: boolean;
  applicability_reason: string;
};
export type SystemLabCase = {
  id: string;
  title: string;
  prediction_label: string;
};
export type SystemLabInputRequest = {
  snapshot_id: string;
  analysis_id: string;
  endpoint_index: number;
  lab_version: string;
  predictions: SystemPredictionsRequest;
};
export type SystemLabPage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Array<SystemLab>;
};
export type SystemLabRun = {
  readonly id: string;
  job: Job;
  snapshot_id: string;
  analysis_id: string;
  readonly endpoint_index: number;
  readonly lab_id: string;
  definition: SystemLab;
  predictions: SystemPredictions;
  observations: Array<SystemObservation>;
  cleanup: SystemCleanup;
  readonly created_at: string;
};
export type SystemLabRunPage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Array<SystemLabRun>;
};
export type SystemObservation = {
  case_id: CaseIdEnum;
  status: SystemObservationStatusEnum;
  hostname: string | null;
  addresses: Array<string>;
  connected: boolean | null;
  pid: number | null;
  return_code: number | null;
  stdout: string;
  timed_out: boolean;
  reaped: boolean | null;
  error_code: string | null;
  elapsed_ms: number;
  observed_at: string;
};
export type SystemObservationStatusEnum =
  'observed' | 'unavailable' | 'invalid';
export type SystemPredictions = {
  first: boolean;
  second: boolean;
};
export type SystemPredictionsRequest = {
  first: boolean;
  second: boolean;
};
export type TargetTypeEnum = 'project' | 'snapshot';
export type TruncationReasonsEnum = 'max_nodes' | 'max_edges';
export type AnalysisWritable = {
  [key: string]: unknown;
};
export type AttemptReviewWritable = {
  attempt_id: string;
  judgement: JudgementEnum;
};
export type AttemptReviewPageWritable = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Array<AttemptReviewWritable>;
};
export type ComparisonHistoryWritable = {
  [key: string]: unknown;
};
export type ComparisonHistoryPageWritable = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Array<ComparisonHistoryWritable>;
};
export type ContextConsentWritable = {
  preview_id: string;
};
export type CurriculumPageWritable = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Array<KnowledgeCurriculumWritable>;
};
export type DeletionPreviewWritable = {
  target_type: TargetTypeEnum;
  target_id: string;
  project_id: string;
  object_name: string;
  scope: DeletionScope;
  confirmation_digest: string;
  can_delete: boolean;
  receiving: boolean;
  busy_jobs: Array<JobWritable>;
};
export type EndpointWritable = {
  method: MethodEnum;
  path: string;
  path_kind: PathKindEnum;
  action: string;
  view: Symbol | null;
  serializer: Symbol | null;
  model: Symbol | null;
  evidence: Array<Evidence>;
};
export type EndpointPageWritable = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Array<EndpointWritable>;
};
export type ExerciseWritable = {
  example_version: string;
  kind: ExerciseKindEnum;
  options: Array<ExerciseOption>;
};
export type ExerciseAttemptWritable = {
  exercise_id: string;
  exercise_version: string;
  answer_version: string;
  example_version: string;
  question: string;
  kind: string;
  snapshot_id: string;
  analysis_id: string;
  feedback: AttemptFeedback;
  previous_attempt_id: string | null;
};
export type ExerciseAttemptPageWritable = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Array<ExerciseAttemptWritable>;
};
export type ExercisePageWritable = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Array<ExerciseWritable>;
};
export type ExplanationWritable = {
  job_id: string;
  preview_id: string;
  analysis_id: string;
  snapshot_id: string;
  endpoint_index: number;
  template_version: string;
  usage: ModelUsage | null;
  content: ExplanationContent;
};
export type ExplanationPageWritable = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Array<ExplanationWritable>;
};
export type FrontendLinkWritable = {
  request_id: string;
  method: string | null;
  path: string | null;
  status: FrontendMatchStatusEnum;
  reason: string;
  source_ref: SourceRef;
};
export type GraphWritable = {
  analysis_id: string;
  snapshot_id: string;
  rule_version: string;
  graph_version: string;
  root_node_id: string | null;
  endpoint_index: number | null;
  algorithm: AlgorithmEnum;
  nodes: Array<GraphNode>;
  edges: Array<GraphEdge>;
  coverage: Coverage;
  diagnostics_url: string;
  total_nodes: number;
  total_edges: number;
  returned_nodes: number;
  returned_edges: number;
  truncated: boolean;
  truncation_reasons: Array<TruncationReasonsEnum>;
};
export type JobWritable = {
  error: Error | null;
};
export type JobPageWritable = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Array<JobWritable>;
};
export type KnowledgeCardPageWritable = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Array<unknown>;
};
export type KnowledgeCurriculumWritable = {
  definition: CurriculumDefinition;
};
export type LabRunWritable = {
  job: JobWritable;
  snapshot_id: string;
  analysis_id: string;
  definition: Lab;
  predictions: Predictions;
  observations: Array<LabObservation>;
  cleanup: LabCleanup;
};
export type LabRunPageWritable = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Array<LabRunWritable>;
};
export type LearningPathWritable = {
  snapshot_id: string;
  analysis_id: string;
  endpoint_index: number;
  curriculum: KnowledgeCurriculumWritable;
  goal: string;
  targets: Array<string>;
  order: Array<string>;
  steps: Array<unknown>;
  applicable: boolean;
  applicability_reason: string;
};
export type MatchedKnowledgeCardWritable = {
  concept_key: string;
  card: unknown;
  mapped: boolean;
  hit_count: number;
  hits: Array<KnowledgeHitPreview>;
  package: KnowledgePackage | null;
};
export type NotificationWritable = {
  job: JobWritable;
  read: boolean;
};
export type NotificationPageWritable = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Array<NotificationWritable>;
  unread_count: number;
  as_of: string;
  read_through: string | null;
};
export type OperationLogWritable = {
  job: JobWritable | null;
};
export type OperationLogPageWritable = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Array<OperationLogWritable>;
};
export type ProjectActivityWritable = {
  active: Array<ProjectActivityItemWritable>;
  recent: Array<ProjectActivityItemWritable>;
};
export type ProjectActivityItemWritable = {
  snapshot: SnapshotWritable | null;
  status: ProjectActivityItemStatusEnum;
  root_count: number | null;
  endpoint_count: number | null;
  stages: Array<ProjectActivityStageWritable>;
};
export type ProjectActivityStageWritable = {
  kind: ProjectActivityStageKindEnum;
  job: JobWritable;
  events: Array<ProjectActivityEvent>;
};
export type ProjectManagementPageWritable = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Array<ProjectSummaryWritable>;
  technologies: Array<string>;
};
export type ProjectPageWritable = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Array<unknown>;
};
export type ProjectSummaryWritable = {
  snapshot_count: number;
  latest_snapshot: SnapshotWritable | null;
  last_imported_at: string | null;
  technologies: Array<ProjectTechnology>;
  root_count: number | null;
  root_path: string | null;
};
export type RelatedOperationLogWritable = {
  job: JobWritable | null;
};
export type RelatedOperationLogPageWritable = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Array<RelatedOperationLogWritable>;
};
export type RelationReviewPageWritable = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Array<unknown>;
  state: RelationReviewState;
};
export type RelationReviewResultWritable = {
  state: RelationReviewState;
};
export type SharedGraphWritable = {
  analysis_id: string;
  snapshot_id: string;
  rule_version: string;
  graph_version: string;
  root_node_id: string | null;
  endpoint_index: number | null;
  algorithm: AlgorithmEnum;
  nodes: Array<GraphNode>;
  edges: Array<GraphEdge>;
  coverage: Coverage;
  diagnostics_url: string;
  total_nodes: number;
  total_edges: number;
  returned_nodes: number;
  returned_edges: number;
  truncated: boolean;
  truncation_reasons: Array<TruncationReasonsEnum>;
  direction: DirectionEnum;
  scope: SharedGraphScopeEnum;
};
export type SnapshotWritable = {
  [key: string]: unknown;
};
export type SnapshotKnowledgePageWritable = {
  count: number;
  next: string | null;
  previous: string | null;
  scan_id: string;
  rule_version: string;
  coverage: KnowledgeCoverage;
  diagnostics: Array<Diagnostic>;
  results: Array<MatchedKnowledgeCardWritable>;
};
export type SnapshotPageWritable = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Array<SnapshotWritable>;
};
export type SnapshotSearchPageWritable = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Array<SnapshotSearchResultWritable>;
};
export type SnapshotSearchResultWritable = {
  snapshot: SnapshotWritable;
};
export type SourceContentWritable = {
  start_line: number;
  end_line: number;
  content: string;
};
export type SourceFilePageWritable = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Array<unknown>;
};
export type SystemCheckWritable = {
  job_id: string;
};
export type SystemLabRunWritable = {
  job: JobWritable;
  snapshot_id: string;
  analysis_id: string;
  definition: SystemLab;
  predictions: SystemPredictions;
  observations: Array<SystemObservation>;
  cleanup: SystemCleanup;
};
export type SystemLabRunPageWritable = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Array<SystemLabRunWritable>;
};
export type AnalysesRetrieveData = {
  body?: never;
  path: {
    analysis_id: string;
  };
  query?: never;
  url: '/api/v1/analyses/{analysis_id}/';
};
export type AnalysesRetrieveErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type AnalysesRetrieveError =
  AnalysesRetrieveErrors[keyof AnalysesRetrieveErrors];
export type AnalysesRetrieveResponses = {
  200: Analysis;
};
export type AnalysesRetrieveResponse =
  AnalysesRetrieveResponses[keyof AnalysesRetrieveResponses];
export type AnalysisDiagnosticsListData = {
  body?: never;
  path: {
    analysis_id: string;
  };
  query?: {
    page?: number;
    page_size?: number;
  };
  url: '/api/v1/analyses/{analysis_id}/diagnostics/';
};
export type AnalysisDiagnosticsListErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type AnalysisDiagnosticsListError =
  AnalysisDiagnosticsListErrors[keyof AnalysisDiagnosticsListErrors];
export type AnalysisDiagnosticsListResponses = {
  200: DiagnosticPage;
};
export type AnalysisDiagnosticsListResponse =
  AnalysisDiagnosticsListResponses[keyof AnalysisDiagnosticsListResponses];
export type EndpointRelationsRetrieveData = {
  body?: never;
  path: {
    analysis_id: string;
  };
  query?: {
    algorithm?: 'bfs' | 'dfs';
    endpoint_index?: number;
    max_edges?: number;
    max_nodes?: number;
    root_node_id?: string;
  };
  url: '/api/v1/analyses/{analysis_id}/endpoint-relations/';
};
export type EndpointRelationsRetrieveErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type EndpointRelationsRetrieveError =
  EndpointRelationsRetrieveErrors[keyof EndpointRelationsRetrieveErrors];
export type EndpointRelationsRetrieveResponses = {
  200: SharedGraph;
};
export type EndpointRelationsRetrieveResponse =
  EndpointRelationsRetrieveResponses[keyof EndpointRelationsRetrieveResponses];
export type AnalysisEndpointsListData = {
  body?: never;
  path: {
    analysis_id: string;
  };
  query?: {
    page?: number;
    page_size?: number;
    q?: string;
  };
  url: '/api/v1/analyses/{analysis_id}/endpoints/';
};
export type AnalysisEndpointsListErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type AnalysisEndpointsListError =
  AnalysisEndpointsListErrors[keyof AnalysisEndpointsListErrors];
export type AnalysisEndpointsListResponses = {
  200: EndpointPage;
};
export type AnalysisEndpointsListResponse =
  AnalysisEndpointsListResponses[keyof AnalysisEndpointsListResponses];
export type AnalysisGraphRetrieveData = {
  body?: never;
  path: {
    analysis_id: string;
  };
  query?: {
    algorithm?: 'bfs' | 'dfs';
    endpoint_index?: number;
    max_edges?: number;
    max_nodes?: number;
    root_node_id?: string;
  };
  url: '/api/v1/analyses/{analysis_id}/graph/';
};
export type AnalysisGraphRetrieveErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type AnalysisGraphRetrieveError =
  AnalysisGraphRetrieveErrors[keyof AnalysisGraphRetrieveErrors];
export type AnalysisGraphRetrieveResponses = {
  200: Graph;
};
export type AnalysisGraphRetrieveResponse =
  AnalysisGraphRetrieveResponses[keyof AnalysisGraphRetrieveResponses];
export type AnalysisImpactRetrieveData = {
  body?: never;
  path: {
    analysis_id: string;
  };
  query: {
    include_candidates?: boolean;
    max_edges?: number;
    max_nodes?: number;
    node_id: string;
  };
  url: '/api/v1/analyses/{analysis_id}/impact/';
};
export type AnalysisImpactRetrieveErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  500: Error;
};
export type AnalysisImpactRetrieveError =
  AnalysisImpactRetrieveErrors[keyof AnalysisImpactRetrieveErrors];
export type AnalysisImpactRetrieveResponses = {
  200: Impact;
};
export type AnalysisImpactRetrieveResponse =
  AnalysisImpactRetrieveResponses[keyof AnalysisImpactRetrieveResponses];
export type RelationReviewsListData = {
  body?: never;
  path: {
    analysis_id: string;
  };
  query: {
    page?: number;
    page_size?: number;
    request_id: string;
  };
  url: '/api/v1/analyses/{analysis_id}/relation-reviews/';
};
export type RelationReviewsListErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type RelationReviewsListError =
  RelationReviewsListErrors[keyof RelationReviewsListErrors];
export type RelationReviewsListResponses = {
  200: RelationReviewPage;
};
export type RelationReviewsListResponse =
  RelationReviewsListResponses[keyof RelationReviewsListResponses];
export type RelationReviewsCreateData = {
  body: RelationReviewInputRequest;
  headers: {
    'Idempotency-Key': string;
    Origin: string;
    'X-CSRFToken': string;
  };
  path: {
    analysis_id: string;
  };
  query?: never;
  url: '/api/v1/analyses/{analysis_id}/relation-reviews/';
};
export type RelationReviewsCreateErrors = {
  403: Error;
  406: Error;
  410: Error;
  500: Error;
};
export type RelationReviewsCreateError =
  RelationReviewsCreateErrors[keyof RelationReviewsCreateErrors];
export type AttemptReviewsListData = {
  body?: never;
  path?: never;
  query: {
    attempt_id: string;
    page?: number;
    page_size?: number;
  };
  url: '/api/v1/attempt-reviews/';
};
export type AttemptReviewsListErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type AttemptReviewsListError =
  AttemptReviewsListErrors[keyof AttemptReviewsListErrors];
export type AttemptReviewsListResponses = {
  200: AttemptReviewPage;
};
export type AttemptReviewsListResponse =
  AttemptReviewsListResponses[keyof AttemptReviewsListResponses];
export type AttemptReviewsCreateData = {
  body: ReviewInputRequest;
  headers: {
    'Idempotency-Key': string;
    Origin: string;
    'X-CSRFToken': string;
  };
  path?: never;
  query?: never;
  url: '/api/v1/attempt-reviews/';
};
export type AttemptReviewsCreateErrors = {
  403: Error;
  406: Error;
  410: Error;
  500: Error;
};
export type AttemptReviewsCreateError =
  AttemptReviewsCreateErrors[keyof AttemptReviewsCreateErrors];
export type ContextPreviewsCreateData = {
  body: PreviewInputRequest;
  headers: {
    'Idempotency-Key': string;
    Origin: string;
    'X-CSRFToken': string;
  };
  path?: never;
  query?: never;
  url: '/api/v1/context-previews/';
};
export type ContextPreviewsCreateErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type ContextPreviewsCreateError =
  ContextPreviewsCreateErrors[keyof ContextPreviewsCreateErrors];
export type ContextPreviewsCreateResponses = {
  200: ContextPreview;
  201: ContextPreview;
};
export type ContextPreviewsCreateResponse =
  ContextPreviewsCreateResponses[keyof ContextPreviewsCreateResponses];
export type ContextPreviewsRetrieveData = {
  body?: never;
  path: {
    preview_id: string;
  };
  query?: never;
  url: '/api/v1/context-previews/{preview_id}/';
};
export type ContextPreviewsRetrieveErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type ContextPreviewsRetrieveError =
  ContextPreviewsRetrieveErrors[keyof ContextPreviewsRetrieveErrors];
export type ContextPreviewsRetrieveResponses = {
  200: ContextPreview;
};
export type ContextPreviewsRetrieveResponse =
  ContextPreviewsRetrieveResponses[keyof ContextPreviewsRetrieveResponses];
export type ContextConsentsCreateData = {
  body: ConsentInputRequest;
  headers: {
    'Idempotency-Key': string;
    Origin: string;
    'X-CSRFToken': string;
  };
  path: {
    preview_id: string;
  };
  query?: never;
  url: '/api/v1/context-previews/{preview_id}/consents/';
};
export type ContextConsentsCreateErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type ContextConsentsCreateError =
  ContextConsentsCreateErrors[keyof ContextConsentsCreateErrors];
export type ContextConsentsCreateResponses = {
  200: ContextConsent;
  201: ContextConsent;
};
export type ContextConsentsCreateResponse =
  ContextConsentsCreateResponses[keyof ContextConsentsCreateResponses];
export type CsrfRetrieveData = {
  body?: never;
  path?: never;
  query?: never;
  url: '/api/v1/csrf/';
};
export type CsrfRetrieveErrors = {
  403: Error;
  406: Error;
  500: Error;
};
export type CsrfRetrieveError = CsrfRetrieveErrors[keyof CsrfRetrieveErrors];
export type CsrfRetrieveResponses = {
  200: Csrf;
};
export type CsrfRetrieveResponse =
  CsrfRetrieveResponses[keyof CsrfRetrieveResponses];
export type ExerciseAttemptsListData = {
  body?: never;
  path?: never;
  query?: {
    analysis_id?: string;
    endpoint_index?: number;
    page?: number;
    page_size?: number;
    snapshot_id?: string;
  };
  url: '/api/v1/exercise-attempts/';
};
export type ExerciseAttemptsListErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type ExerciseAttemptsListError =
  ExerciseAttemptsListErrors[keyof ExerciseAttemptsListErrors];
export type ExerciseAttemptsListResponses = {
  200: ExerciseAttemptPage;
};
export type ExerciseAttemptsListResponse =
  ExerciseAttemptsListResponses[keyof ExerciseAttemptsListResponses];
export type ExerciseAttemptsCreateData = {
  body: AttemptInputRequest;
  headers: {
    'Idempotency-Key': string;
    Origin: string;
    'X-CSRFToken': string;
  };
  path?: never;
  query?: never;
  url: '/api/v1/exercise-attempts/';
};
export type ExerciseAttemptsCreateErrors = {
  403: Error;
  406: Error;
  410: Error;
  500: Error;
};
export type ExerciseAttemptsCreateError =
  ExerciseAttemptsCreateErrors[keyof ExerciseAttemptsCreateErrors];
export type ExerciseAttemptsRetrieveData = {
  body?: never;
  path: {
    attempt_id: string;
  };
  query?: never;
  url: '/api/v1/exercise-attempts/{attempt_id}/';
};
export type ExerciseAttemptsRetrieveErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type ExerciseAttemptsRetrieveError =
  ExerciseAttemptsRetrieveErrors[keyof ExerciseAttemptsRetrieveErrors];
export type ExerciseAttemptsRetrieveResponses = {
  200: ExerciseAttempt;
};
export type ExerciseAttemptsRetrieveResponse =
  ExerciseAttemptsRetrieveResponses[keyof ExerciseAttemptsRetrieveResponses];
export type ExercisesListData = {
  body?: never;
  path?: never;
  query: {
    analysis_id: string;
    endpoint_index: number;
    page?: number;
    page_size?: number;
  };
  url: '/api/v1/exercises/';
};
export type ExercisesListErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type ExercisesListError = ExercisesListErrors[keyof ExercisesListErrors];
export type ExercisesListResponses = {
  200: ExercisePage;
};
export type ExercisesListResponse =
  ExercisesListResponses[keyof ExercisesListResponses];
export type ExercisesRetrieveData = {
  body?: never;
  path: {
    exercise_id: string;
  };
  query: {
    analysis_id: string;
    endpoint_index: number;
  };
  url: '/api/v1/exercises/{exercise_id}/';
};
export type ExercisesRetrieveErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type ExercisesRetrieveError =
  ExercisesRetrieveErrors[keyof ExercisesRetrieveErrors];
export type ExercisesRetrieveResponses = {
  200: Exercise;
};
export type ExercisesRetrieveResponse =
  ExercisesRetrieveResponses[keyof ExercisesRetrieveResponses];
export type ExplanationsListData = {
  body?: never;
  path?: never;
  query?: {
    analysis_id?: string;
    endpoint_index?: number;
    page?: number;
    page_size?: number;
    snapshot_id?: string;
  };
  url: '/api/v1/explanations/';
};
export type ExplanationsListErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type ExplanationsListError =
  ExplanationsListErrors[keyof ExplanationsListErrors];
export type ExplanationsListResponses = {
  200: ExplanationPage;
};
export type ExplanationsListResponse =
  ExplanationsListResponses[keyof ExplanationsListResponses];
export type ExplanationsCreateData = {
  body: ExplanationInputRequest;
  headers: {
    'Idempotency-Key': string;
    Origin: string;
    'X-CSRFToken': string;
  };
  path?: never;
  query?: never;
  url: '/api/v1/explanations/';
};
export type ExplanationsCreateErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type ExplanationsCreateError =
  ExplanationsCreateErrors[keyof ExplanationsCreateErrors];
export type ExplanationsCreateResponses = {
  200: Job;
  202: Job;
};
export type ExplanationsCreateResponse =
  ExplanationsCreateResponses[keyof ExplanationsCreateResponses];
export type ExplanationsRetrieveData = {
  body?: never;
  path: {
    explanation_id: string;
  };
  query?: never;
  url: '/api/v1/explanations/{explanation_id}/';
};
export type ExplanationsRetrieveErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type ExplanationsRetrieveError =
  ExplanationsRetrieveErrors[keyof ExplanationsRetrieveErrors];
export type ExplanationsRetrieveResponses = {
  200: Explanation;
};
export type ExplanationsRetrieveResponse =
  ExplanationsRetrieveResponses[keyof ExplanationsRetrieveResponses];
export type JobsListData = {
  body?: never;
  path?: never;
  query?: {
    kind?:
      | 'analysis'
      | 'delete'
      | 'explanation'
      | 'import'
      | 'lab'
      | 'snapshot_comparison'
      | 'source_scan'
      | 'system_check';
    page?: number;
    page_size?: number;
    snapshot_id?: string;
  };
  url: '/api/v1/jobs/';
};
export type JobsListErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  410: Error;
  500: Error;
  503: Error;
};
export type JobsListError = JobsListErrors[keyof JobsListErrors];
export type JobsListResponses = {
  200: JobPage;
};
export type JobsListResponse = JobsListResponses[keyof JobsListResponses];
export type JobsRetrieveData = {
  body?: never;
  path: {
    job_id: string;
  };
  query?: never;
  url: '/api/v1/jobs/{job_id}/';
};
export type JobsRetrieveErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  410: Error;
  500: Error;
  503: Error;
};
export type JobsRetrieveError = JobsRetrieveErrors[keyof JobsRetrieveErrors];
export type JobsRetrieveResponses = {
  200: Job;
};
export type JobsRetrieveResponse =
  JobsRetrieveResponses[keyof JobsRetrieveResponses];
export type FolderImportsRetryData = {
  body: FolderInputRequest;
  headers: {
    'Idempotency-Key': string;
    Origin: string;
    'X-CSRFToken': string;
  };
  path: {
    job_id: string;
  };
  query?: never;
  url: '/api/v1/jobs/{job_id}/folder-retries/';
};
export type FolderImportsRetryErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type FolderImportsRetryError =
  FolderImportsRetryErrors[keyof FolderImportsRetryErrors];
export type FolderImportsRetryResponses = {
  200: Job;
  202: Job;
};
export type FolderImportsRetryResponse =
  FolderImportsRetryResponses[keyof FolderImportsRetryResponses];
export type JobsRetryData = {
  body:
    | {
        [key: string]: never;
      }
    | {
        consent_id: string;
      };
  headers: {
    'Idempotency-Key': string;
    Origin: string;
    'X-CSRFToken': string;
  };
  path: {
    job_id: string;
  };
  query?: never;
  url: '/api/v1/jobs/{job_id}/retries/';
};
export type JobsRetryErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type JobsRetryError = JobsRetryErrors[keyof JobsRetryErrors];
export type JobsRetryResponses = {
  200: Job;
  202: Job;
};
export type JobsRetryResponse = JobsRetryResponses[keyof JobsRetryResponses];
export type KnowledgeCardsListData = {
  body?: never;
  path?: never;
  query?: {
    page?: number;
    page_size?: number;
  };
  url: '/api/v1/knowledge-cards/';
};
export type KnowledgeCardsListErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type KnowledgeCardsListError =
  KnowledgeCardsListErrors[keyof KnowledgeCardsListErrors];
export type KnowledgeCardsListResponses = {
  200: KnowledgeCardPage;
};
export type KnowledgeCardsListResponse =
  KnowledgeCardsListResponses[keyof KnowledgeCardsListResponses];
export type KnowledgeCardsRetrieveData = {
  body?: never;
  path: {
    card_id: string;
  };
  query?: never;
  url: '/api/v1/knowledge-cards/{card_id}/';
};
export type KnowledgeCardsRetrieveErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type KnowledgeCardsRetrieveError =
  KnowledgeCardsRetrieveErrors[keyof KnowledgeCardsRetrieveErrors];
export type KnowledgeCardsRetrieveResponses = {
  200: KnowledgeCard;
};
export type KnowledgeCardsRetrieveResponse =
  KnowledgeCardsRetrieveResponses[keyof KnowledgeCardsRetrieveResponses];
export type KnowledgeCurriculaListData = {
  body?: never;
  path?: never;
  query?: {
    page?: number;
    page_size?: number;
  };
  url: '/api/v1/knowledge-curricula/';
};
export type KnowledgeCurriculaListErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type KnowledgeCurriculaListError =
  KnowledgeCurriculaListErrors[keyof KnowledgeCurriculaListErrors];
export type KnowledgeCurriculaListResponses = {
  200: CurriculumPage;
};
export type KnowledgeCurriculaListResponse =
  KnowledgeCurriculaListResponses[keyof KnowledgeCurriculaListResponses];
export type KnowledgeCurriculaRetrieveData = {
  body?: never;
  path: {
    curriculum_id: string;
  };
  query?: never;
  url: '/api/v1/knowledge-curricula/{curriculum_id}/';
};
export type KnowledgeCurriculaRetrieveErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type KnowledgeCurriculaRetrieveError =
  KnowledgeCurriculaRetrieveErrors[keyof KnowledgeCurriculaRetrieveErrors];
export type KnowledgeCurriculaRetrieveResponses = {
  200: KnowledgeCurriculum;
};
export type KnowledgeCurriculaRetrieveResponse =
  KnowledgeCurriculaRetrieveResponses[keyof KnowledgeCurriculaRetrieveResponses];
export type CurriculumProgressRetrieveData = {
  body?: never;
  path: {
    curriculum_id: string;
  };
  query?: never;
  url: '/api/v1/knowledge-curricula/{curriculum_id}/progress/';
};
export type CurriculumProgressRetrieveErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type CurriculumProgressRetrieveError =
  CurriculumProgressRetrieveErrors[keyof CurriculumProgressRetrieveErrors];
export type CurriculumProgressRetrieveResponses = {
  200: CurriculumProgress;
};
export type CurriculumProgressRetrieveResponse =
  CurriculumProgressRetrieveResponses[keyof CurriculumProgressRetrieveResponses];
export type CurriculumCardProgressUpdateData = {
  body: PatchedCurriculumProgressInputRequest;
  headers: {
    Origin: string;
    'X-CSRFToken': string;
  };
  path: {
    card_id: string;
    curriculum_id: string;
  };
  query?: never;
  url: '/api/v1/knowledge-curricula/{curriculum_id}/progress/{card_id}/';
};
export type CurriculumCardProgressUpdateErrors = {
  403: Error;
  406: Error;
  410: Error;
  500: Error;
};
export type CurriculumCardProgressUpdateError =
  CurriculumCardProgressUpdateErrors[keyof CurriculumCardProgressUpdateErrors];
export type LabRunsListData = {
  body?: never;
  path?: never;
  query?: {
    analysis_id?: string;
    endpoint_index?: number;
    job_id?: string;
    page?: number;
    page_size?: number;
  };
  url: '/api/v1/lab-runs/';
};
export type LabRunsListErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type LabRunsListError = LabRunsListErrors[keyof LabRunsListErrors];
export type LabRunsListResponses = {
  200: LabRunPage;
};
export type LabRunsListResponse =
  LabRunsListResponses[keyof LabRunsListResponses];
export type LabRunsRetrieveData = {
  body?: never;
  path: {
    run_id: string;
  };
  query?: never;
  url: '/api/v1/lab-runs/{run_id}/';
};
export type LabRunsRetrieveErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type LabRunsRetrieveError =
  LabRunsRetrieveErrors[keyof LabRunsRetrieveErrors];
export type LabRunsRetrieveResponses = {
  200: LabRun;
};
export type LabRunsRetrieveResponse =
  LabRunsRetrieveResponses[keyof LabRunsRetrieveResponses];
export type LabsListData = {
  body?: never;
  path?: never;
  query: {
    analysis_id: string;
    endpoint_index: number;
    page?: number;
    page_size?: number;
  };
  url: '/api/v1/labs/';
};
export type LabsListErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type LabsListError = LabsListErrors[keyof LabsListErrors];
export type LabsListResponses = {
  200: LabPage;
};
export type LabsListResponse = LabsListResponses[keyof LabsListResponses];
export type LabsRetrieveData = {
  body?: never;
  path: {
    lab_id: string;
  };
  query: {
    analysis_id: string;
    endpoint_index: number;
  };
  url: '/api/v1/labs/{lab_id}/';
};
export type LabsRetrieveErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type LabsRetrieveError = LabsRetrieveErrors[keyof LabsRetrieveErrors];
export type LabsRetrieveResponses = {
  200: Lab;
};
export type LabsRetrieveResponse =
  LabsRetrieveResponses[keyof LabsRetrieveResponses];
export type LabRunsCreateData = {
  body: LabInputRequest;
  headers: {
    'Idempotency-Key': string;
    Origin: string;
    'X-CSRFToken': string;
  };
  path: {
    lab_id: string;
  };
  query?: never;
  url: '/api/v1/labs/{lab_id}/runs/';
};
export type LabRunsCreateErrors = {
  403: Error;
  406: Error;
  410: Error;
  500: Error;
};
export type LabRunsCreateError = LabRunsCreateErrors[keyof LabRunsCreateErrors];
export type LearningPathsRetrieveData = {
  body?: never;
  path?: never;
  query: {
    analysis_id: string;
    curriculum_id: string;
    endpoint_index: number;
    goal?: string;
  };
  url: '/api/v1/learning-paths/';
};
export type LearningPathsRetrieveErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type LearningPathsRetrieveError =
  LearningPathsRetrieveErrors[keyof LearningPathsRetrieveErrors];
export type LearningPathsRetrieveResponses = {
  200: LearningPath;
};
export type LearningPathsRetrieveResponse =
  LearningPathsRetrieveResponses[keyof LearningPathsRetrieveResponses];
export type NotificationReadStateUpdateData = {
  body: PatchedNotificationReadStateInputRequest;
  headers: {
    Origin: string;
    'X-CSRFToken': string;
  };
  path?: never;
  query?: never;
  url: '/api/v1/notification-read-state/';
};
export type NotificationReadStateUpdateErrors = {
  403: Error;
  406: Error;
  410: Error;
  500: Error;
};
export type NotificationReadStateUpdateError =
  NotificationReadStateUpdateErrors[keyof NotificationReadStateUpdateErrors];
export type NotificationsListData = {
  body?: never;
  path?: never;
  query?: {
    page?: number;
    page_size?: number;
  };
  url: '/api/v1/notifications/';
};
export type NotificationsListErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type NotificationsListError =
  NotificationsListErrors[keyof NotificationsListErrors];
export type NotificationsListResponses = {
  200: NotificationPage;
};
export type NotificationsListResponse =
  NotificationsListResponses[keyof NotificationsListResponses];
export type NotificationsMarkReadData = {
  body: PatchedNotificationReadInputRequest;
  headers: {
    Origin: string;
    'X-CSRFToken': string;
  };
  path: {
    job_id: string;
  };
  query?: never;
  url: '/api/v1/notifications/{job_id}/';
};
export type NotificationsMarkReadErrors = {
  403: Error;
  406: Error;
  410: Error;
  500: Error;
};
export type NotificationsMarkReadError =
  NotificationsMarkReadErrors[keyof NotificationsMarkReadErrors];
export type OperationLogsListData = {
  body?: never;
  path?: never;
  query?: {
    ended_after?: string;
    ended_before?: string;
    operation?: string;
    ordering?: string;
    page?: number;
    page_size?: number;
    project_id?: string;
    q?: string;
    result?: string;
    started_after?: string;
    started_before?: string;
    view?: string;
  };
  url: '/api/v1/operation-logs/';
};
export type OperationLogsListErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  500: Error;
  503: Error;
};
export type OperationLogsListError =
  OperationLogsListErrors[keyof OperationLogsListErrors];
export type OperationLogsListResponses = {
  200: OperationLogPage;
};
export type OperationLogsListResponse =
  OperationLogsListResponses[keyof OperationLogsListResponses];
export type OperationLogsRetrieveData = {
  body?: never;
  path: {
    log_id: string;
  };
  query?: never;
  url: '/api/v1/operation-logs/{log_id}/';
};
export type OperationLogsRetrieveErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  500: Error;
  503: Error;
};
export type OperationLogsRetrieveError =
  OperationLogsRetrieveErrors[keyof OperationLogsRetrieveErrors];
export type OperationLogsRetrieveResponses = {
  200: OperationLog;
};
export type OperationLogsRetrieveResponse =
  OperationLogsRetrieveResponses[keyof OperationLogsRetrieveResponses];
export type OperationLogsHistoryData = {
  body?: never;
  path: {
    log_id: string;
  };
  query?: {
    page?: number;
    page_size?: number;
  };
  url: '/api/v1/operation-logs/{log_id}/history/';
};
export type OperationLogsHistoryErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  500: Error;
  503: Error;
};
export type OperationLogsHistoryError =
  OperationLogsHistoryErrors[keyof OperationLogsHistoryErrors];
export type OperationLogsHistoryResponses = {
  200: OperationLogPage;
};
export type OperationLogsHistoryResponse =
  OperationLogsHistoryResponses[keyof OperationLogsHistoryResponses];
export type OperationLogsRelatedData = {
  body?: never;
  path: {
    log_id: string;
  };
  query?: {
    page?: number;
    page_size?: number;
  };
  url: '/api/v1/operation-logs/{log_id}/related/';
};
export type OperationLogsRelatedErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  500: Error;
  503: Error;
};
export type OperationLogsRelatedError =
  OperationLogsRelatedErrors[keyof OperationLogsRelatedErrors];
export type OperationLogsRelatedResponses = {
  200: RelatedOperationLogPage;
};
export type OperationLogsRelatedResponse =
  OperationLogsRelatedResponses[keyof OperationLogsRelatedResponses];
export type OperationLogsExportData = {
  body?: never;
  path?: never;
  query?: {
    ended_after?: string;
    ended_before?: string;
    operation?: string;
    ordering?: string;
    project_id?: string;
    q?: string;
    result?: string;
    started_after?: string;
    started_before?: string;
    view?: string;
  };
  url: '/api/v1/operation-logs/export/';
};
export type OperationLogsExportErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  413: Error;
  500: Error;
  503: Error;
};
export type OperationLogsExportError =
  OperationLogsExportErrors[keyof OperationLogsExportErrors];
export type OperationLogsExportResponses = {
  200: Blob | File;
};
export type OperationLogsExportResponse =
  OperationLogsExportResponses[keyof OperationLogsExportResponses];
export type OperationLogsStatisticsData = {
  body?: never;
  path?: never;
  query?: {
    ended_after?: string;
    ended_before?: string;
    operation?: string;
    ordering?: string;
    page?: number;
    page_size?: number;
    project_id?: string;
    q?: string;
    result?: string;
    started_after?: string;
    started_before?: string;
    view?: string;
  };
  url: '/api/v1/operation-logs/statistics/';
};
export type OperationLogsStatisticsErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  500: Error;
  503: Error;
};
export type OperationLogsStatisticsError =
  OperationLogsStatisticsErrors[keyof OperationLogsStatisticsErrors];
export type OperationLogsStatisticsResponses = {
  200: OperationStatistics;
};
export type OperationLogsStatisticsResponse =
  OperationLogsStatisticsResponses[keyof OperationLogsStatisticsResponses];
export type ProjectsListData = {
  body?: never;
  path?: never;
  query?: {
    page?: number;
    page_size?: number;
    q?: string;
  };
  url: '/api/v1/projects/';
};
export type ProjectsListErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type ProjectsListError = ProjectsListErrors[keyof ProjectsListErrors];
export type ProjectsListResponses = {
  200: ProjectPage;
};
export type ProjectsListResponse =
  ProjectsListResponses[keyof ProjectsListResponses];
export type ProjectsCreateData = {
  body: ProjectInputRequest;
  headers: {
    'Idempotency-Key': string;
    Origin: string;
    'X-CSRFToken': string;
  };
  path?: never;
  query?: never;
  url: '/api/v1/projects/';
};
export type ProjectsCreateErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type ProjectsCreateError =
  ProjectsCreateErrors[keyof ProjectsCreateErrors];
export type ProjectsCreateResponses = {
  200: Project;
  201: Project;
};
export type ProjectsCreateResponse =
  ProjectsCreateResponses[keyof ProjectsCreateResponses];
export type ProjectsDeleteData = {
  body?: never;
  headers: {
    'Idempotency-Key': string;
    Origin: string;
    'X-CSRFToken': string;
  };
  path: {
    project_id: string;
  };
  query?: never;
  url: '/api/v1/projects/{project_id}/';
};
export type ProjectsDeleteErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type ProjectsDeleteError =
  ProjectsDeleteErrors[keyof ProjectsDeleteErrors];
export type ProjectsDeleteResponses = {
  200: Job;
  202: Job;
};
export type ProjectsDeleteResponse =
  ProjectsDeleteResponses[keyof ProjectsDeleteResponses];
export type ProjectsRetrieveData = {
  body?: never;
  path: {
    project_id: string;
  };
  query?: never;
  url: '/api/v1/projects/{project_id}/';
};
export type ProjectsRetrieveErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type ProjectsRetrieveError =
  ProjectsRetrieveErrors[keyof ProjectsRetrieveErrors];
export type ProjectsRetrieveResponses = {
  200: Project;
};
export type ProjectsRetrieveResponse =
  ProjectsRetrieveResponses[keyof ProjectsRetrieveResponses];
export type ProjectDeletionPreviewData = {
  body?: never;
  path: {
    project_id: string;
  };
  query?: never;
  url: '/api/v1/projects/{project_id}/deletion-preview/';
};
export type ProjectDeletionPreviewErrors = {
  403: Error;
  404: Error;
  406: Error;
  500: Error;
  503: Error;
};
export type ProjectDeletionPreviewError =
  ProjectDeletionPreviewErrors[keyof ProjectDeletionPreviewErrors];
export type ProjectDeletionPreviewResponses = {
  200: DeletionPreview;
};
export type ProjectDeletionPreviewResponse =
  ProjectDeletionPreviewResponses[keyof ProjectDeletionPreviewResponses];
export type FolderImportsCreateData = {
  body: FolderInputRequest;
  headers: {
    'Idempotency-Key': string;
    Origin: string;
    'X-CSRFToken': string;
  };
  path: {
    project_id: string;
  };
  query?: never;
  url: '/api/v1/projects/{project_id}/folder-imports/';
};
export type FolderImportsCreateErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type FolderImportsCreateError =
  FolderImportsCreateErrors[keyof FolderImportsCreateErrors];
export type FolderImportsCreateResponses = {
  200: Job;
  202: Job;
};
export type FolderImportsCreateResponse =
  FolderImportsCreateResponses[keyof FolderImportsCreateResponses];
export type ImportsCreateData = {
  body: ImportInputRequest;
  headers: {
    'Idempotency-Key': string;
    Origin: string;
    'X-CSRFToken': string;
  };
  path: {
    project_id: string;
  };
  query?: never;
  url: '/api/v1/projects/{project_id}/imports/';
};
export type ImportsCreateErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type ImportsCreateError = ImportsCreateErrors[keyof ImportsCreateErrors];
export type ImportsCreateResponses = {
  200: Job;
  202: Job;
};
export type ImportsCreateResponse =
  ImportsCreateResponses[keyof ImportsCreateResponses];
export type ProjectSnapshotComparisonsListData = {
  body?: never;
  path: {
    project_id: string;
  };
  query?: {
    page?: number;
    page_size?: number;
  };
  url: '/api/v1/projects/{project_id}/snapshot-comparisons/';
};
export type ProjectSnapshotComparisonsListErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type ProjectSnapshotComparisonsListError =
  ProjectSnapshotComparisonsListErrors[keyof ProjectSnapshotComparisonsListErrors];
export type ProjectSnapshotComparisonsListResponses = {
  200: ComparisonHistoryPage;
};
export type ProjectSnapshotComparisonsListResponse =
  ProjectSnapshotComparisonsListResponses[keyof ProjectSnapshotComparisonsListResponses];
export type ProjectSnapshotComparisonsCreateData = {
  body: ComparisonInputRequest;
  headers: {
    'Idempotency-Key': string;
    Origin: string;
    'X-CSRFToken': string;
  };
  path: {
    project_id: string;
  };
  query?: never;
  url: '/api/v1/projects/{project_id}/snapshot-comparisons/';
};
export type ProjectSnapshotComparisonsCreateErrors = {
  403: Error;
  406: Error;
  410: Error;
  500: Error;
};
export type ProjectSnapshotComparisonsCreateError =
  ProjectSnapshotComparisonsCreateErrors[keyof ProjectSnapshotComparisonsCreateErrors];
export type SnapshotsListData = {
  body?: never;
  path: {
    project_id: string;
  };
  query?: {
    page?: number;
    page_size?: number;
  };
  url: '/api/v1/projects/{project_id}/snapshots/';
};
export type SnapshotsListErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type SnapshotsListError = SnapshotsListErrors[keyof SnapshotsListErrors];
export type SnapshotsListResponses = {
  200: SnapshotPage;
};
export type SnapshotsListResponse =
  SnapshotsListResponses[keyof SnapshotsListResponses];
export type ProjectsActivityRetrieveData = {
  body?: never;
  path?: never;
  query?: never;
  url: '/api/v1/projects/activity/';
};
export type ProjectsActivityRetrieveErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type ProjectsActivityRetrieveError =
  ProjectsActivityRetrieveErrors[keyof ProjectsActivityRetrieveErrors];
export type ProjectsActivityRetrieveResponses = {
  200: ProjectActivity;
};
export type ProjectsActivityRetrieveResponse =
  ProjectsActivityRetrieveResponses[keyof ProjectsActivityRetrieveResponses];
export type ProjectsManagementListData = {
  body?: never;
  path?: never;
  query?: {
    ordering?: 'created' | 'name' | 'recent_import';
    page?: number;
    page_size?: number;
    q?: string;
    technology?: string;
  };
  url: '/api/v1/projects/management/';
};
export type ProjectsManagementListErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type ProjectsManagementListError =
  ProjectsManagementListErrors[keyof ProjectsManagementListErrors];
export type ProjectsManagementListResponses = {
  200: ProjectManagementPage;
};
export type ProjectsManagementListResponse =
  ProjectsManagementListResponses[keyof ProjectsManagementListResponses];
export type SnapshotComparisonsRetrieveData = {
  body?: never;
  path: {
    comparison_id: string;
  };
  query?: never;
  url: '/api/v1/snapshot-comparisons/{comparison_id}/';
};
export type SnapshotComparisonsRetrieveErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type SnapshotComparisonsRetrieveError =
  SnapshotComparisonsRetrieveErrors[keyof SnapshotComparisonsRetrieveErrors];
export type SnapshotComparisonsRetrieveResponses = {
  200: SnapshotComparison;
};
export type SnapshotComparisonsRetrieveResponse =
  SnapshotComparisonsRetrieveResponses[keyof SnapshotComparisonsRetrieveResponses];
export type ComparisonFilesListData = {
  body?: never;
  path: {
    comparison_id: string;
  };
  query?: {
    page?: number;
    page_size?: number;
  };
  url: '/api/v1/snapshot-comparisons/{comparison_id}/files/';
};
export type ComparisonFilesListErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type ComparisonFilesListError =
  ComparisonFilesListErrors[keyof ComparisonFilesListErrors];
export type ComparisonFilesListResponses = {
  200: ComparisonFilePage;
};
export type ComparisonFilesListResponse =
  ComparisonFilesListResponses[keyof ComparisonFilesListResponses];
export type ComparisonFilesRetrieveData = {
  body?: never;
  path: {
    change_id: string;
    comparison_id: string;
  };
  query?: never;
  url: '/api/v1/snapshot-comparisons/{comparison_id}/files/{change_id}/';
};
export type ComparisonFilesRetrieveErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type ComparisonFilesRetrieveError =
  ComparisonFilesRetrieveErrors[keyof ComparisonFilesRetrieveErrors];
export type ComparisonFilesRetrieveResponses = {
  200: ComparisonFileDetail;
};
export type ComparisonFilesRetrieveResponse =
  ComparisonFilesRetrieveResponses[keyof ComparisonFilesRetrieveResponses];
export type ComparisonImpactRetrieveData = {
  body?: never;
  path: {
    comparison_id: string;
  };
  query?: {
    change_id?: string;
    include_candidates?: boolean;
    max_edges?: number;
    max_nodes?: number;
  };
  url: '/api/v1/snapshot-comparisons/{comparison_id}/impact/';
};
export type ComparisonImpactRetrieveErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  500: Error;
};
export type ComparisonImpactRetrieveError =
  ComparisonImpactRetrieveErrors[keyof ComparisonImpactRetrieveErrors];
export type ComparisonImpactRetrieveResponses = {
  200: ComparisonImpact;
};
export type ComparisonImpactRetrieveResponse =
  ComparisonImpactRetrieveResponses[keyof ComparisonImpactRetrieveResponses];
export type SnapshotsSearchData = {
  body?: never;
  path?: never;
  query?: {
    page?: number;
    page_size?: number;
    q?: string;
  };
  url: '/api/v1/snapshots/';
};
export type SnapshotsSearchErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type SnapshotsSearchError =
  SnapshotsSearchErrors[keyof SnapshotsSearchErrors];
export type SnapshotsSearchResponses = {
  200: SnapshotSearchPage;
};
export type SnapshotsSearchResponse =
  SnapshotsSearchResponses[keyof SnapshotsSearchResponses];
export type SnapshotsDeleteData = {
  body?: never;
  headers: {
    'Idempotency-Key': string;
    Origin: string;
    'X-CSRFToken': string;
  };
  path: {
    snapshot_id: string;
  };
  query?: never;
  url: '/api/v1/snapshots/{snapshot_id}/';
};
export type SnapshotsDeleteErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type SnapshotsDeleteError =
  SnapshotsDeleteErrors[keyof SnapshotsDeleteErrors];
export type SnapshotsDeleteResponses = {
  200: Job;
  202: Job;
};
export type SnapshotsDeleteResponse =
  SnapshotsDeleteResponses[keyof SnapshotsDeleteResponses];
export type SnapshotsRetrieveData = {
  body?: never;
  path: {
    snapshot_id: string;
  };
  query?: never;
  url: '/api/v1/snapshots/{snapshot_id}/';
};
export type SnapshotsRetrieveErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type SnapshotsRetrieveError =
  SnapshotsRetrieveErrors[keyof SnapshotsRetrieveErrors];
export type SnapshotsRetrieveResponses = {
  200: Snapshot;
};
export type SnapshotsRetrieveResponse =
  SnapshotsRetrieveResponses[keyof SnapshotsRetrieveResponses];
export type SnapshotsRenameData = {
  body: PatchedSnapshotNameInputRequest;
  headers: {
    Origin: string;
    'X-CSRFToken': string;
  };
  path: {
    snapshot_id: string;
  };
  query?: never;
  url: '/api/v1/snapshots/{snapshot_id}/';
};
export type SnapshotsRenameErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type SnapshotsRenameError =
  SnapshotsRenameErrors[keyof SnapshotsRenameErrors];
export type SnapshotsRenameResponses = {
  200: Snapshot;
};
export type SnapshotsRenameResponse =
  SnapshotsRenameResponses[keyof SnapshotsRenameResponses];
export type AnalysesCreateData = {
  body: AnalysisInputRequest;
  headers: {
    'Idempotency-Key': string;
    Origin: string;
    'X-CSRFToken': string;
  };
  path: {
    snapshot_id: string;
  };
  query?: never;
  url: '/api/v1/snapshots/{snapshot_id}/analyses/';
};
export type AnalysesCreateErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type AnalysesCreateError =
  AnalysesCreateErrors[keyof AnalysesCreateErrors];
export type AnalysesCreateResponses = {
  200: Job;
  202: Job;
};
export type AnalysesCreateResponse =
  AnalysesCreateResponses[keyof AnalysesCreateResponses];
export type SnapshotDeletionPreviewData = {
  body?: never;
  path: {
    snapshot_id: string;
  };
  query?: never;
  url: '/api/v1/snapshots/{snapshot_id}/deletion-preview/';
};
export type SnapshotDeletionPreviewErrors = {
  403: Error;
  404: Error;
  406: Error;
  500: Error;
  503: Error;
};
export type SnapshotDeletionPreviewError =
  SnapshotDeletionPreviewErrors[keyof SnapshotDeletionPreviewErrors];
export type SnapshotDeletionPreviewResponses = {
  200: DeletionPreview;
};
export type SnapshotDeletionPreviewResponse =
  SnapshotDeletionPreviewResponses[keyof SnapshotDeletionPreviewResponses];
export type SnapshotFilesListData = {
  body?: never;
  path: {
    snapshot_id: string;
  };
  query?: {
    page?: number;
    page_size?: number;
  };
  url: '/api/v1/snapshots/{snapshot_id}/files/';
};
export type SnapshotFilesListErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type SnapshotFilesListError =
  SnapshotFilesListErrors[keyof SnapshotFilesListErrors];
export type SnapshotFilesListResponses = {
  200: SourceFilePage;
};
export type SnapshotFilesListResponse =
  SnapshotFilesListResponses[keyof SnapshotFilesListResponses];
export type SnapshotFileContentRetrieveData = {
  body?: never;
  path: {
    file_id: string;
    snapshot_id: string;
  };
  query?: {
    end_line?: number;
    start_line?: number;
  };
  url: '/api/v1/snapshots/{snapshot_id}/files/{file_id}/content/';
};
export type SnapshotFileContentRetrieveErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type SnapshotFileContentRetrieveError =
  SnapshotFileContentRetrieveErrors[keyof SnapshotFileContentRetrieveErrors];
export type SnapshotFileContentRetrieveResponses = {
  200: SourceContent;
};
export type SnapshotFileContentRetrieveResponse =
  SnapshotFileContentRetrieveResponses[keyof SnapshotFileContentRetrieveResponses];
export type SnapshotFileEvidenceListData = {
  body?: never;
  path: {
    file_id: string;
    snapshot_id: string;
  };
  query?: {
    analysis_id?: string;
    page?: number;
    page_size?: number;
    scan_id?: string;
  };
  url: '/api/v1/snapshots/{snapshot_id}/files/{file_id}/evidence/';
};
export type SnapshotFileEvidenceListErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  500: Error;
};
export type SnapshotFileEvidenceListError =
  SnapshotFileEvidenceListErrors[keyof SnapshotFileEvidenceListErrors];
export type SnapshotFileEvidenceListResponses = {
  200: SourceEvidencePage;
};
export type SnapshotFileEvidenceListResponse =
  SnapshotFileEvidenceListResponses[keyof SnapshotFileEvidenceListResponses];
export type SnapshotKnowledgeCardsListData = {
  body?: never;
  path: {
    snapshot_id: string;
  };
  query?: {
    analysis_id?: string;
    concept_key?: string;
    endpoint_index?: string;
    file_path?: string;
    page?: number;
    page_size?: number;
    scan_id?: string;
  };
  url: '/api/v1/snapshots/{snapshot_id}/knowledge-cards/';
};
export type SnapshotKnowledgeCardsListErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type SnapshotKnowledgeCardsListError =
  SnapshotKnowledgeCardsListErrors[keyof SnapshotKnowledgeCardsListErrors];
export type SnapshotKnowledgeCardsListResponses = {
  200: SnapshotKnowledgePage;
};
export type SnapshotKnowledgeCardsListResponse =
  SnapshotKnowledgeCardsListResponses[keyof SnapshotKnowledgeCardsListResponses];
export type SnapshotKnowledgeHitsListData = {
  body?: never;
  path: {
    snapshot_id: string;
  };
  query?: {
    analysis_id?: string;
    concept_key?: string;
    endpoint_index?: string;
    file_path?: string;
    page?: number;
    page_size?: number;
    scan_id?: string;
  };
  url: '/api/v1/snapshots/{snapshot_id}/knowledge-hits/';
};
export type SnapshotKnowledgeHitsListErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type SnapshotKnowledgeHitsListError =
  SnapshotKnowledgeHitsListErrors[keyof SnapshotKnowledgeHitsListErrors];
export type SnapshotKnowledgeHitsListResponses = {
  200: KnowledgeHitPage;
};
export type SnapshotKnowledgeHitsListResponse =
  SnapshotKnowledgeHitsListResponses[keyof SnapshotKnowledgeHitsListResponses];
export type SourceScansCreateData = {
  body?: never;
  headers: {
    'Idempotency-Key': string;
    Origin: string;
    'X-CSRFToken': string;
  };
  path: {
    snapshot_id: string;
  };
  query?: never;
  url: '/api/v1/snapshots/{snapshot_id}/source-scans/';
};
export type SourceScansCreateErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type SourceScansCreateError =
  SourceScansCreateErrors[keyof SourceScansCreateErrors];
export type SourceScansCreateResponses = {
  200: Job;
  202: Job;
};
export type SourceScansCreateResponse =
  SourceScansCreateResponses[keyof SourceScansCreateResponses];
export type SourceScansRetrieveData = {
  body?: never;
  path: {
    scan_id: string;
  };
  query?: never;
  url: '/api/v1/source-scans/{scan_id}/';
};
export type SourceScansRetrieveErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type SourceScansRetrieveError =
  SourceScansRetrieveErrors[keyof SourceScansRetrieveErrors];
export type SourceScansRetrieveResponses = {
  200: SourceScan;
};
export type SourceScansRetrieveResponse =
  SourceScansRetrieveResponses[keyof SourceScansRetrieveResponses];
export type SystemChecksCreateData = {
  body: {
    [key: string]: never;
  };
  headers: {
    'Idempotency-Key': string;
    Origin: string;
    'X-CSRFToken': string;
  };
  path?: never;
  query?: never;
  url: '/api/v1/system-checks/';
};
export type SystemChecksCreateErrors = {
  403: Error;
  406: Error;
  410: Error;
  500: Error;
};
export type SystemChecksCreateError =
  SystemChecksCreateErrors[keyof SystemChecksCreateErrors];
export type SystemChecksRetrieveData = {
  body?: never;
  path: {
    check_id: string;
  };
  query?: never;
  url: '/api/v1/system-checks/{check_id}/';
};
export type SystemChecksRetrieveErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  410: Error;
  500: Error;
  503: Error;
};
export type SystemChecksRetrieveError =
  SystemChecksRetrieveErrors[keyof SystemChecksRetrieveErrors];
export type SystemChecksRetrieveResponses = {
  200: SystemCheck;
};
export type SystemChecksRetrieveResponse =
  SystemChecksRetrieveResponses[keyof SystemChecksRetrieveResponses];
export type SystemLabRunsListData = {
  body?: never;
  path?: never;
  query?: {
    analysis_id?: string;
    endpoint_index?: number;
    job_id?: string;
    page?: number;
    page_size?: number;
  };
  url: '/api/v1/system-lab-runs/';
};
export type SystemLabRunsListErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type SystemLabRunsListError =
  SystemLabRunsListErrors[keyof SystemLabRunsListErrors];
export type SystemLabRunsListResponses = {
  200: SystemLabRunPage;
};
export type SystemLabRunsListResponse =
  SystemLabRunsListResponses[keyof SystemLabRunsListResponses];
export type SystemLabRunsRetrieveData = {
  body?: never;
  path: {
    run_id: string;
  };
  query?: never;
  url: '/api/v1/system-lab-runs/{run_id}/';
};
export type SystemLabRunsRetrieveErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type SystemLabRunsRetrieveError =
  SystemLabRunsRetrieveErrors[keyof SystemLabRunsRetrieveErrors];
export type SystemLabRunsRetrieveResponses = {
  200: SystemLabRun;
};
export type SystemLabRunsRetrieveResponse =
  SystemLabRunsRetrieveResponses[keyof SystemLabRunsRetrieveResponses];
export type SystemLabsListData = {
  body?: never;
  path?: never;
  query: {
    analysis_id: string;
    endpoint_index: number;
    page?: number;
    page_size?: number;
  };
  url: '/api/v1/system-labs/';
};
export type SystemLabsListErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type SystemLabsListError =
  SystemLabsListErrors[keyof SystemLabsListErrors];
export type SystemLabsListResponses = {
  200: SystemLabPage;
};
export type SystemLabsListResponse =
  SystemLabsListResponses[keyof SystemLabsListResponses];
export type SystemLabsRetrieveData = {
  body?: never;
  path: {
    lab_id: string;
  };
  query: {
    analysis_id: string;
    endpoint_index: number;
  };
  url: '/api/v1/system-labs/{lab_id}/';
};
export type SystemLabsRetrieveErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  409: Error;
  410: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type SystemLabsRetrieveError =
  SystemLabsRetrieveErrors[keyof SystemLabsRetrieveErrors];
export type SystemLabsRetrieveResponses = {
  200: SystemLab;
};
export type SystemLabsRetrieveResponse =
  SystemLabsRetrieveResponses[keyof SystemLabsRetrieveResponses];
export type SystemLabRunsCreateData = {
  body: SystemLabInputRequest;
  headers: {
    'Idempotency-Key': string;
    Origin: string;
    'X-CSRFToken': string;
  };
  path: {
    lab_id: string;
  };
  query?: never;
  url: '/api/v1/system-labs/{lab_id}/runs/';
};
export type SystemLabRunsCreateErrors = {
  403: Error;
  406: Error;
  410: Error;
  500: Error;
};
export type SystemLabRunsCreateError =
  SystemLabRunsCreateErrors[keyof SystemLabRunsCreateErrors];
