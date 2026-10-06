import { useEffect, useMemo, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import type { KnowledgeCurriculum } from '../../shared/api/generated/schema';
import { ApiError } from '../../shared/api/client';
import { Feedback } from '../../shared/components/Feedback';
import { PageControls } from '../../shared/components/PageControls';
import { getCurriculum, listCurricula } from './api/paths-api';
import {
  courseProgressKey,
  getCourseCard,
  getCourseProgress,
  setCourseCardProgress,
} from './api/course-api';
import './CourseReader.css';

function CourseReading({
  course,
  active,
}: {
  course: KnowledgeCurriculum;
  active: boolean;
}) {
  const cache = useQueryClient();
  const key = useMemo(
    () => courseProgressKey(course.id, course.version),
    [course.id, course.version],
  );
  const [cardId, setCardId] = useState<string | null>(null);
  const [focusRequest, setFocusRequest] = useState(0);
  const [operation, setOperation] = useState({
    pending: false,
    unknown: false,
    error: null as Error | null,
  });
  const body = useRef<HTMLDivElement>(null);
  const focusFrame = useRef(0);
  const focusTarget = useRef<string | null>(null);
  const alive = useRef(false);
  const pending = useRef(false);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
      cancelAnimationFrame(focusFrame.current);
      controller.current?.abort();
      // 离开期间未确定的写入只使原课程缓存失效，重新进入先读服务端。
      if (pending.current)
        void cache.invalidateQueries({
          queryKey: key,
          exact: true,
          refetchType: 'none',
        });
    };
  }, [cache, key]);
  const progress = useQuery({
    queryKey: key,
    queryFn: ({ signal }) => getCourseProgress(course, signal),
    enabled: active,
  });
  const current =
    progress.data?.cards.find((card) => card.card_id === cardId) ??
    progress.data?.cards[0];
  const card = useQuery({
    queryKey: [
      'learning',
      'course-card',
      course.id,
      course.version,
      current?.card_id,
    ],
    queryFn: ({ signal }) => getCourseCard(current!, signal),
    enabled: active && !!current,
  });

  useEffect(() => {
    if (!active) {
      focusTarget.current = null;
      return;
    }
    const id = focusTarget.current;
    if (!id || card.data?.id !== id) return;
    // 正文可能需异步读取，只有用户选卡且该版本已渲染后才定位。
    focusFrame.current = requestAnimationFrame(() => {
      focusFrame.current = requestAnimationFrame(() => {
        focusFrame.current = 0;
        const reading = body.current;
        if (reading?.dataset.cardId === id && !reading.closest('[hidden]'))
          reading.focus({ preventScroll: true });
        focusTarget.current = null;
      });
    });
    return () => cancelAnimationFrame(focusFrame.current);
  }, [active, card.data?.id, focusRequest]);

  function choose(id: string) {
    setCardId(id);
    focusTarget.current = id;
    setFocusRequest((value) => value + 1);
  }

  async function save(completed: boolean) {
    if (
      !active ||
      pending.current ||
      operation.unknown ||
      !current ||
      !card.data ||
      progress.isFetching
    )
      return;
    pending.current = true;
    const request = new AbortController();
    controller.current = request;
    setOperation({ pending: true, unknown: false, error: null });
    try {
      await cache.cancelQueries({ queryKey: key, exact: true });
      const result = await setCourseCardProgress(
        course,
        current,
        completed,
        request.signal,
      );
      if (!alive.current) return;
      cache.setQueryData(key, result);
      void cache.invalidateQueries({ queryKey: key, exact: true });
      setOperation({ pending: false, unknown: false, error: null });
    } catch (error) {
      if (!alive.current) return;
      const rejected =
        error instanceof ApiError && error.status >= 400 && error.status < 500;
      setOperation({
        pending: false,
        unknown: !rejected,
        error:
          error instanceof Error
            ? error
            : new ApiError('保存阅读状态失败，请核实服务端状态。', 0),
      });
    } finally {
      pending.current = false;
      controller.current = null;
    }
  }

  async function verify() {
    const result = await progress.refetch();
    if (alive.current && result.isSuccess)
      setOperation({ pending: false, unknown: false, error: null });
  }

  return (
    <section aria-label="课程阅读内容">
      <h3>
        {course.title} · {course.version}
      </h3>
      <p>这里保存已阅读状态，不评价掌握程度，也不改变练习成绩或先修顺序。</p>
      <Feedback error={progress.error} retry={() => void progress.refetch()} />
      <Feedback error={operation.error} />
      {progress.isPending && active && <p role="status">读取课程已阅读状态…</p>}
      {progress.data && (
        <>
          <div className="course-reading-progress" data-page-keep>
            <span>
              已阅读 {progress.data.completed_count} /{' '}
              {progress.data.total_count}
            </span>
            <progress
              aria-label="当前课程已阅读进度"
              max={progress.data.total_count}
              value={progress.data.completed_count}
            />
          </div>
          <div className="course-reading-grid">
            <nav className="course-card-directory" aria-label="课程卡片目录">
              <ul>
                {progress.data.cards.map((item) => (
                  <li key={item.card_id}>
                    <button
                      type="button"
                      aria-pressed={current?.card_id === item.card_id}
                      onClick={() => choose(item.card_id)}
                    >
                      {item.title}
                      <small>
                        {item.completed ? '已阅读' : '未标记'} · v{item.version}
                      </small>
                    </button>
                  </li>
                ))}
              </ul>
            </nav>
            <div
              ref={body}
              className="course-reader-body"
              role="region"
              aria-label="课程卡片正文区域"
              tabIndex={-1}
              data-card-id={card.data?.id}
            >
              <Feedback error={card.error} retry={() => void card.refetch()} />
              {card.isPending && active && <p role="status">读取课程卡片…</p>}
              {card.data && current && (
                <>
                  <article aria-label="课程卡片正文">
                    <h4>
                      {card.data.title} · v{card.data.version}
                    </h4>
                    <p>{card.data.body}</p>
                    <small>{card.data.applicability}</small>
                    <details>
                      <summary>内容维护说明</summary>
                      <p>{card.data.review_note}</p>
                    </details>
                  </article>
                  <div className="course-reader-actions" data-page-keep>
                    <button
                      type="button"
                      disabled={
                        !active ||
                        operation.pending ||
                        operation.unknown ||
                        progress.isFetching
                      }
                      onClick={() => void save(!current.completed)}
                    >
                      {operation.pending
                        ? '保存阅读状态…'
                        : current.completed
                          ? '撤销已阅读'
                          : '标记已阅读'}
                    </button>
                    {operation.unknown && (
                      <button
                        type="button"
                        disabled={!active || progress.isFetching}
                        onClick={() => void verify()}
                      >
                        核实已阅读状态
                      </button>
                    )}
                  </div>
                </>
              )}
              {operation.unknown && (
                <p role="note">
                  保存结果尚未确定，请先核实服务端状态；不会自动重发标记。
                </p>
              )}
            </div>
          </div>
        </>
      )}
    </section>
  );
}

export function CourseReader({
  courseId,
  onSelectCourse,
  active = true,
}: {
  courseId: string | null;
  onSelectCourse: (id: string) => void;
  active?: boolean;
}) {
  const [page, setPage] = useState(1);
  const [focusRequest, setFocusRequest] = useState(0);
  const reading = useRef<HTMLDivElement>(null);
  const focusTarget = useRef<string | null>(null);
  const focusFrame = useRef(0);
  const courses = useQuery({
    queryKey: ['learning', 'curricula', page],
    queryFn: ({ signal }) => listCurricula(page, signal),
    enabled: active,
  });
  const course = useQuery({
    queryKey: ['learning', 'curriculum', courseId],
    queryFn: ({ signal }) => getCurriculum(courseId!, signal),
    enabled: active && !!courseId,
  });
  useEffect(() => {
    if (!active) {
      focusTarget.current = null;
      return;
    }
    const id = focusTarget.current;
    if (!id || course.data?.id !== id) return;
    focusFrame.current = requestAnimationFrame(() => {
      focusFrame.current = requestAnimationFrame(() => {
        focusFrame.current = 0;
        if (
          reading.current?.dataset.courseId === id &&
          !reading.current.closest('[hidden]')
        )
          reading.current.focus({ preventScroll: true });
        focusTarget.current = null;
      });
    });
    return () => cancelAnimationFrame(focusFrame.current);
  }, [active, course.data?.id, focusRequest]);
  function chooseCourse(id: string) {
    focusTarget.current = id;
    setFocusRequest((value) => value + 1);
    onSelectCourse(id);
  }
  return (
    <section className="course-reader" aria-label="独立课程阅读">
      <h2>课程目录</h2>
      <p>
        直接阅读已发布课程，无需先选择项目或接口。阅读标记按课程版本独立保存。
      </p>
      <Feedback error={courses.error} retry={() => void courses.refetch()} />
      {courses.isPending && active && <p role="status">读取发布课程…</p>}
      {courses.data?.count === 0 && <p>暂无已发布课程。</p>}
      <ul className="course-catalog-list">
        {courses.data?.results.map((item) => (
          <li key={item.id}>
            <button
              type="button"
              aria-current={courseId === item.id ? 'page' : undefined}
              onClick={() => chooseCourse(item.id)}
            >
              {item.title} · {item.version}
            </button>
          </li>
        ))}
      </ul>
      {courses.data && (courses.data.next || courses.data.previous) && (
        <PageControls
          page={page}
          previous={courses.data.previous}
          next={courses.data.next}
          onPage={setPage}
        />
      )}
      <Feedback error={course.error} retry={() => void course.refetch()} />
      {courseId && course.isPending && active && (
        <p role="status">读取所选课程…</p>
      )}
      {!courseId && <p role="note">选择一门课程开始阅读。</p>}
      {course.data && (
        <div
          ref={reading}
          role="region"
          aria-label="所选课程阅读"
          tabIndex={-1}
          data-course-id={course.data.id}
        >
          <CourseReading
            key={course.data.id + '.' + course.data.version}
            course={course.data}
            active={active}
          />
        </div>
      )}
    </section>
  );
}
