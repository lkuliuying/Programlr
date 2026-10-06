import { useQuery } from '@tanstack/react-query';
import type { KnowledgeCurriculum } from '../../shared/api/generated/schema';
import { Feedback } from '../../shared/components/Feedback';
import { listCurricula } from './api/paths-api';
import { courseProgressKey, getCourseProgress } from './api/course-api';
import './CourseReader.css';

function CourseSummaryRow({
  course,
  active,
  onSelectCourse,
}: {
  course: KnowledgeCurriculum;
  active: boolean;
  onSelectCourse: (id: string) => void;
}) {
  const progress = useQuery({
    queryKey: courseProgressKey(course.id, course.version),
    queryFn: ({ signal }) => getCourseProgress(course, signal),
    enabled: active,
  });
  return (
    <li data-page-keep>
      <button
        type="button"
        className="course-summary-choice"
        onClick={() => onSelectCourse(course.id)}
      >
        <strong>{course.title}</strong>
        <small>课程版本 {course.version}</small>
      </button>
      <Feedback error={progress.error} retry={() => void progress.refetch()} />
      {progress.isPending && active && <p role="status">读取已阅读进度…</p>}
      {progress.data && (
        <div className="course-reading-progress">
          <span>
            已阅读 {progress.data.completed_count} / {progress.data.total_count}
          </span>
          <progress
            aria-label={`${course.title}已阅读进度`}
            max={progress.data.total_count}
            value={progress.data.completed_count}
          />
        </div>
      )}
    </li>
  );
}

export function CourseSummary({
  onSelectCourse,
  active = true,
}: {
  onSelectCourse: (id: string) => void;
  active?: boolean;
}) {
  const courses = useQuery({
    queryKey: ['learning', 'curricula', 1],
    queryFn: ({ signal }) => listCurricula(1, signal),
    enabled: active,
  });
  return (
    <section className="course-summary" aria-label="课程进度">
      <p className="muted">
        按课程版本保存已阅读状态，不代表掌握程度或练习成绩。
      </p>
      <Feedback error={courses.error} retry={() => void courses.refetch()} />
      {courses.isPending && active && <p role="status">读取发布课程…</p>}
      {courses.data?.count === 0 && <p>暂无已发布课程。</p>}
      <ul className="course-summary-list">
        {courses.data?.results.slice(0, 3).map((course) => (
          <CourseSummaryRow
            key={course.id + '.' + course.version}
            course={course}
            active={active}
            onSelectCourse={onSelectCourse}
          />
        ))}
      </ul>
    </section>
  );
}
