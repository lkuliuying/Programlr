// 从本工程 ../contracts/openapi.yaml 自动生成，请勿手工修改。
export type ClientOptions = {
  baseUrl: `${string}://${string}` | (string & {});
};
export type Csrf = {
  csrf_token: string;
};
export type Error = {
  code: string;
  message: string;
  details: {
    [key: string]: unknown;
  };
  request_id: string;
};
export type Task = {
  readonly id: string;
  title: string;
  readonly created_at: string;
};
export type TaskPage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Array<Task>;
};
export type TaskRequest = {
  title: string;
};
export type TaskWritable = {
  title: string;
};
export type TaskPageWritable = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Array<TaskWritable>;
};
export type TaskBoardCsrfRetrieveData = {
  body?: never;
  path?: never;
  query?: never;
  url: '/api/v1/csrf/';
};
export type TaskBoardCsrfRetrieveErrors = {
  403: Error;
  406: Error;
  500: Error;
};
export type TaskBoardCsrfRetrieveError =
  TaskBoardCsrfRetrieveErrors[keyof TaskBoardCsrfRetrieveErrors];
export type TaskBoardCsrfRetrieveResponses = {
  200: Csrf;
};
export type TaskBoardCsrfRetrieveResponse =
  TaskBoardCsrfRetrieveResponses[keyof TaskBoardCsrfRetrieveResponses];
export type TaskBoardTasksListData = {
  body?: never;
  path?: never;
  query?: {
    page?: number;
    page_size?: number;
  };
  url: '/api/v1/tasks/';
};
export type TaskBoardTasksListErrors = {
  400: Error;
  403: Error;
  404: Error;
  406: Error;
  500: Error;
  503: Error;
};
export type TaskBoardTasksListError =
  TaskBoardTasksListErrors[keyof TaskBoardTasksListErrors];
export type TaskBoardTasksListResponses = {
  200: TaskPage;
};
export type TaskBoardTasksListResponse =
  TaskBoardTasksListResponses[keyof TaskBoardTasksListResponses];
export type TaskBoardTasksCreateData = {
  body: TaskRequest;
  headers: {
    'Idempotency-Key': string;
    Origin: string;
    'X-CSRFToken': string;
  };
  path?: never;
  query?: never;
  url: '/api/v1/tasks/';
};
export type TaskBoardTasksCreateErrors = {
  400: Error;
  403: Error;
  406: Error;
  409: Error;
  413: Error;
  415: Error;
  500: Error;
  503: Error;
};
export type TaskBoardTasksCreateError =
  TaskBoardTasksCreateErrors[keyof TaskBoardTasksCreateErrors];
export type TaskBoardTasksCreateResponses = {
  200: Task;
  201: Task;
};
export type TaskBoardTasksCreateResponse =
  TaskBoardTasksCreateResponses[keyof TaskBoardTasksCreateResponses];
