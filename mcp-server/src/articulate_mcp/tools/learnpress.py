"""MCP tools for LearnPress LMS management via REST API."""

import logging
import httpx
from mcp.server.fastmcp import FastMCP

from articulate_mcp.connection_manager import connection_manager
from articulate_mcp.context_helper import get_connection_info

logger = logging.getLogger("articulate-mcp")


async def _get_lp_client(connection_id: int, user_id: int, namespace: str = "learnpress/v1"):
    """Get an httpx client configured for LearnPress REST API."""
    connection = await connection_manager.get_connection(connection_id, user_id)
    if not connection:
        raise ValueError("Connection not found")

    wp_url = connection["wp_url"].rstrip("/")
    wp_user = connection["wp_user"]
    wp_pass = connection["wp_app_password"]

    return httpx.AsyncClient(
        base_url=f"{wp_url}/wp-json/{namespace}",
        auth=(wp_user, wp_pass),
        timeout=30.0,
    )


async def _get_wp_client(connection_id: int, user_id: int):
    """Get an httpx client for standard WP REST API (wp/v2)."""
    connection = await connection_manager.get_connection(connection_id, user_id)
    if not connection:
        raise ValueError("Connection not found")

    wp_url = connection["wp_url"].rstrip("/")
    wp_user = connection["wp_user"]
    wp_pass = connection["wp_app_password"]

    return httpx.AsyncClient(
        base_url=f"{wp_url}/wp-json/wp/v2",
        auth=(wp_user, wp_pass),
        timeout=30.0,
    )


def register(mcp: FastMCP) -> None:
    """Register LearnPress LMS tools."""

    # ── Phase 1: Course Management ──────────────────────────────

    @mcp.tool()
    async def lp_list_courses(
        search: str = "",
        category: str = "",
        per_page: int = 10,
        page: int = 1,
        context=None,
    ) -> str:
        """List LearnPress courses with optional filtering.

        Args:
            search: Search by course title or content
            category: Filter by course category slug
            per_page: Number of results per page (max 100)
            page: Page number
        """
        connection_id, user_id = get_connection_info(context)

        async with await _get_lp_client(connection_id, user_id) as client:
            params = {"per_page": min(per_page, 100), "page": page}
            if search:
                params["search"] = search
            if category:
                params["category"] = category

            resp = await client.get("/courses", params=params)
            if resp.status_code == 404:
                return "LearnPress is not installed or the courses endpoint is unavailable."
            resp.raise_for_status()

            courses = resp.json()
            if not courses:
                return "No courses found."

            lines = [f"LearnPress Courses ({len(courses)}):"]
            for c in courses:
                title = c.get("title", {})
                if isinstance(title, dict):
                    title = title.get("rendered", "Untitled")
                status = c.get("status", "unknown")
                course_id = c.get("id", "?")
                lines.append(f"  - [{course_id}] {title} (status: {status})")
            return "\n".join(lines)

    @mcp.tool()
    async def lp_get_course(
        course_id: int,
        context=None,
    ) -> str:
        """Get detailed information about a LearnPress course.

        Args:
            course_id: The course post ID
        """
        connection_id, user_id = get_connection_info(context)

        async with await _get_lp_client(connection_id, user_id) as client:
            resp = await client.get(f"/courses/{course_id}")
            if resp.status_code == 404:
                return f"Course {course_id} not found."
            resp.raise_for_status()

            c = resp.json()
            title = c.get("title", {})
            if isinstance(title, dict):
                title = title.get("rendered", "Untitled")
            content = c.get("content", {})
            if isinstance(content, dict):
                content = content.get("rendered", "")

            sections = c.get("sections", [])
            section_lines = []
            for s in sections:
                s_title = s.get("title", "Untitled Section")
                items = s.get("items", [])
                section_lines.append(f"  Section: {s_title}")
                for item in items:
                    i_title = item.get("title", "Untitled")
                    i_type = item.get("type", "lesson")
                    section_lines.append(f"    - [{i_type}] {i_title} (ID: {item.get('id', '?')})")

            lines = [
                f"Course: {title}",
                f"ID: {c.get('id', '?')}",
                f"Status: {c.get('status', 'unknown')}",
                f"Price: {c.get('price', 'Free')}",
                f"Students: {c.get('count_students', 0)}",
                f"Duration: {c.get('duration', 'N/A')}",
            ]
            if section_lines:
                lines.append("\nCurriculum:")
                lines.extend(section_lines)

            return "\n".join(lines)

    @mcp.tool()
    async def lp_create_course(
        title: str,
        content: str = "",
        status: str = "draft",
        context=None,
    ) -> str:
        """Create a new LearnPress course.

        Args:
            title: Course title
            content: Course description (HTML)
            status: Post status (draft, publish, pending)
        """
        connection_id, user_id = get_connection_info(context)

        async with await _get_wp_client(connection_id, user_id) as client:
            payload = {
                "title": title,
                "content": content,
                "status": status,
            }
            resp = await client.post("/lp_course", json=payload)
            if resp.status_code == 403:
                return "Error: Your WordPress user lacks permission to create courses."
            resp.raise_for_status()

            course = resp.json()
            return (
                f"Created course:\n"
                f"  Title: {title}\n"
                f"  ID: {course.get('id', '?')}\n"
                f"  Status: {course.get('status', status)}"
            )

    @mcp.tool()
    async def lp_update_course(
        course_id: int,
        title: str = "",
        content: str = "",
        status: str = "",
        context=None,
    ) -> str:
        """Update an existing LearnPress course.

        Args:
            course_id: The course post ID
            title: New course title (leave empty to keep current)
            content: New course description (leave empty to keep current)
            status: New status (draft, publish, pending; leave empty to keep current)
        """
        connection_id, user_id = get_connection_info(context)

        payload = {}
        if title:
            payload["title"] = title
        if content:
            payload["content"] = content
        if status:
            payload["status"] = status

        if not payload:
            return "No fields to update."

        async with await _get_wp_client(connection_id, user_id) as client:
            resp = await client.post(f"/lp_course/{course_id}", json=payload)
            if resp.status_code == 404:
                return f"Course {course_id} not found."
            if resp.status_code == 403:
                return "Error: Your WordPress user lacks permission to update courses."
            resp.raise_for_status()

            course = resp.json()
            return f"Updated course {course_id} successfully."

    @mcp.tool()
    async def lp_delete_course(
        course_id: int,
        context=None,
    ) -> str:
        """Delete a LearnPress course.

        Args:
            course_id: The course post ID to delete
        """
        connection_id, user_id = get_connection_info(context)

        async with await _get_wp_client(connection_id, user_id) as client:
            resp = await client.delete(f"/lp_course/{course_id}", params={"force": True})
            if resp.status_code == 404:
                return f"Course {course_id} not found."
            if resp.status_code == 403:
                return "Error: Your WordPress user lacks permission to delete courses."
            resp.raise_for_status()

            return f"Deleted course {course_id}."

    @mcp.tool()
    async def lp_list_lessons(
        search: str = "",
        per_page: int = 20,
        page: int = 1,
        context=None,
    ) -> str:
        """List LearnPress lessons.

        Args:
            search: Search by lesson title
            per_page: Results per page (max 100)
            page: Page number
        """
        connection_id, user_id = get_connection_info(context)

        async with await _get_lp_client(connection_id, user_id) as client:
            params = {"per_page": min(per_page, 100), "page": page}
            if search:
                params["search"] = search

            resp = await client.get("/lessons", params=params)
            if resp.status_code == 404:
                return "LearnPress lessons endpoint not available."
            resp.raise_for_status()

            lessons = resp.json()
            if not lessons:
                return "No lessons found."

            lines = [f"LearnPress Lessons ({len(lessons)}):"]
            for l in lessons:
                title = l.get("title", {})
                if isinstance(title, dict):
                    title = title.get("rendered", "Untitled")
                lines.append(f"  - [{l.get('id', '?')}] {title}")
            return "\n".join(lines)

    @mcp.tool()
    async def lp_get_lesson(
        lesson_id: int,
        context=None,
    ) -> str:
        """Get detailed information about a LearnPress lesson.

        Args:
            lesson_id: The lesson post ID
        """
        connection_id, user_id = get_connection_info(context)

        async with await _get_lp_client(connection_id, user_id) as client:
            resp = await client.get(f"/lessons/{lesson_id}")
            if resp.status_code == 404:
                return f"Lesson {lesson_id} not found."
            resp.raise_for_status()

            l = resp.json()
            title = l.get("title", {})
            if isinstance(title, dict):
                title = title.get("rendered", "Untitled")
            content = l.get("content", {})
            if isinstance(content, dict):
                content = content.get("rendered", "")

            return (
                f"Lesson: {title}\n"
                f"ID: {l.get('id', '?')}\n"
                f"Status: {l.get('status', 'unknown')}\n"
                f"Duration: {l.get('duration', 'N/A')}\n"
                f"Content length: {len(content)} chars"
            )

    @mcp.tool()
    async def lp_create_lesson(
        title: str,
        content: str = "",
        status: str = "draft",
        context=None,
    ) -> str:
        """Create a new LearnPress lesson.

        Args:
            title: Lesson title
            content: Lesson content (HTML)
            status: Post status (draft, publish)
        """
        connection_id, user_id = get_connection_info(context)

        async with await _get_wp_client(connection_id, user_id) as client:
            resp = await client.post("/lp_lesson", json={
                "title": title,
                "content": content,
                "status": status,
            })
            if resp.status_code == 403:
                return "Error: Your WordPress user lacks permission to create lessons."
            resp.raise_for_status()

            lesson = resp.json()
            return f"Created lesson: {title} (ID: {lesson.get('id', '?')})"

    @mcp.tool()
    async def lp_list_quizzes(
        search: str = "",
        per_page: int = 20,
        page: int = 1,
        context=None,
    ) -> str:
        """List LearnPress quizzes.

        Args:
            search: Search by quiz title
            per_page: Results per page (max 100)
            page: Page number
        """
        connection_id, user_id = get_connection_info(context)

        async with await _get_lp_client(connection_id, user_id) as client:
            params = {"per_page": min(per_page, 100), "page": page}
            if search:
                params["search"] = search

            resp = await client.get("/quiz", params=params)
            if resp.status_code == 404:
                return "LearnPress quizzes endpoint not available."
            resp.raise_for_status()

            quizzes = resp.json()
            if not quizzes:
                return "No quizzes found."

            lines = [f"LearnPress Quizzes ({len(quizzes)}):"]
            for q in quizzes:
                title = q.get("title", {})
                if isinstance(title, dict):
                    title = title.get("rendered", "Untitled")
                lines.append(f"  - [{q.get('id', '?')}] {title}")
            return "\n".join(lines)

    @mcp.tool()
    async def lp_get_quiz(
        quiz_id: int,
        context=None,
    ) -> str:
        """Get detailed information about a LearnPress quiz including questions.

        Args:
            quiz_id: The quiz post ID
        """
        connection_id, user_id = get_connection_info(context)

        async with await _get_lp_client(connection_id, user_id) as client:
            resp = await client.get(f"/quiz/{quiz_id}")
            if resp.status_code == 404:
                return f"Quiz {quiz_id} not found."
            resp.raise_for_status()

            q = resp.json()
            title = q.get("title", {})
            if isinstance(title, dict):
                title = title.get("rendered", "Untitled")

            questions = q.get("questions", [])
            q_lines = []
            for i, question in enumerate(questions, 1):
                q_title = question.get("title", "Untitled")
                q_type = question.get("type", "unknown")
                q_lines.append(f"  {i}. [{q_type}] {q_title}")

            lines = [
                f"Quiz: {title}",
                f"ID: {q.get('id', '?')}",
                f"Status: {q.get('status', 'unknown')}",
                f"Duration: {q.get('duration', 'N/A')}",
                f"Passing Grade: {q.get('passing_grade', 'N/A')}",
                f"Questions: {len(questions)}",
            ]
            if q_lines:
                lines.append("\nQuestion List:")
                lines.extend(q_lines)

            return "\n".join(lines)

    @mcp.tool()
    async def lp_create_quiz(
        title: str,
        content: str = "",
        status: str = "draft",
        context=None,
    ) -> str:
        """Create a new LearnPress quiz.

        Args:
            title: Quiz title
            content: Quiz description (HTML)
            status: Post status (draft, publish)
        """
        connection_id, user_id = get_connection_info(context)

        async with await _get_wp_client(connection_id, user_id) as client:
            resp = await client.post("/lp_quiz", json={
                "title": title,
                "content": content,
                "status": status,
            })
            if resp.status_code == 403:
                return "Error: Your WordPress user lacks permission to create quizzes."
            resp.raise_for_status()

            quiz = resp.json()
            return f"Created quiz: {title} (ID: {quiz.get('id', '?')})"

    # ── Phase 2: Enrollment & Progress ──────────────────────────

    @mcp.tool()
    async def lp_enroll_student(
        course_id: int,
        context=None,
    ) -> str:
        """Enroll the current user in a LearnPress course.

        Args:
            course_id: The course ID to enroll in
        """
        connection_id, user_id = get_connection_info(context)

        async with await _get_lp_client(connection_id, user_id) as client:
            resp = await client.post("/courses/enroll", json={"id": course_id})
            if resp.status_code == 404:
                return f"Course {course_id} not found."
            if resp.status_code in (400, 403):
                data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                return f"Enrollment failed: {data.get('message', resp.text)}"
            resp.raise_for_status()

            return f"Successfully enrolled in course {course_id}."

    @mcp.tool()
    async def lp_finish_course(
        course_id: int,
        context=None,
    ) -> str:
        """Mark a LearnPress course as complete for the current user.

        Args:
            course_id: The course ID to finish
        """
        connection_id, user_id = get_connection_info(context)

        async with await _get_lp_client(connection_id, user_id) as client:
            resp = await client.post("/courses/finish", json={"id": course_id})
            if resp.status_code in (400, 403):
                data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                return f"Cannot finish course: {data.get('message', resp.text)}"
            resp.raise_for_status()

            return f"Course {course_id} marked as complete."

    @mcp.tool()
    async def lp_retake_course(
        course_id: int,
        context=None,
    ) -> str:
        """Retake a LearnPress course (reset progress).

        Args:
            course_id: The course ID to retake
        """
        connection_id, user_id = get_connection_info(context)

        async with await _get_lp_client(connection_id, user_id) as client:
            resp = await client.post("/courses/retake", json={"id": course_id})
            if resp.status_code in (400, 403):
                data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                return f"Cannot retake course: {data.get('message', resp.text)}"
            resp.raise_for_status()

            return f"Course {course_id} reset for retake."

    @mcp.tool()
    async def lp_list_enrolled_courses(
        per_page: int = 20,
        page: int = 1,
        context=None,
    ) -> str:
        """List courses the current user is enrolled in.

        Args:
            per_page: Results per page
            page: Page number
        """
        connection_id, user_id = get_connection_info(context)

        async with await _get_lp_client(connection_id, user_id) as client:
            resp = await client.get("/courses", params={
                "learned": "true",
                "per_page": min(per_page, 100),
                "page": page,
            })
            resp.raise_for_status()

            courses = resp.json()
            if not courses:
                return "Not enrolled in any courses."

            lines = [f"Enrolled Courses ({len(courses)}):"]
            for c in courses:
                title = c.get("title", {})
                if isinstance(title, dict):
                    title = title.get("rendered", "Untitled")
                lines.append(f"  - [{c.get('id', '?')}] {title}")
            return "\n".join(lines)

    @mcp.tool()
    async def lp_get_student_progress(
        context=None,
    ) -> str:
        """Get the current user's student statistics and progress."""
        connection_id, user_id = get_connection_info(context)

        async with await _get_lp_client(connection_id, user_id, namespace="lp/v1") as client:
            resp = await client.get("/profile/student/statistic")
            if resp.status_code == 404:
                return "Student profile endpoint not available."
            resp.raise_for_status()

            stats = resp.json()
            if not stats:
                return "No student progress data available."

            lines = ["Student Progress:"]
            if isinstance(stats, dict):
                for key, value in stats.items():
                    lines.append(f"  {key}: {value}")
            else:
                lines.append(f"  {stats}")
            return "\n".join(lines)

    @mcp.tool()
    async def lp_start_quiz(
        quiz_id: int,
        context=None,
    ) -> str:
        """Start a quiz attempt.

        Args:
            quiz_id: The quiz post ID to start
        """
        connection_id, user_id = get_connection_info(context)

        async with await _get_lp_client(connection_id, user_id) as client:
            resp = await client.post("/quiz/start", json={"id": quiz_id})
            if resp.status_code == 404:
                return f"Quiz {quiz_id} not found."
            if resp.status_code in (400, 403):
                data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                return f"Cannot start quiz: {data.get('message', resp.text)}"
            resp.raise_for_status()

            data = resp.json()
            return f"Quiz {quiz_id} started. {data.get('message', '')}"

    @mcp.tool()
    async def lp_submit_quiz(
        quiz_id: int,
        answered: str = "",
        context=None,
    ) -> str:
        """Submit answers and finish a quiz.

        Args:
            quiz_id: The quiz post ID
            answered: JSON string of answered questions (format depends on quiz type)
        """
        connection_id, user_id = get_connection_info(context)

        import json
        answers = {}
        if answered:
            try:
                answers = json.loads(answered)
            except json.JSONDecodeError:
                return "Error: 'answered' must be a valid JSON string."

        async with await _get_lp_client(connection_id, user_id) as client:
            payload = {"id": quiz_id}
            if answers:
                payload["answered"] = answers

            resp = await client.post("/quiz/finish", json=payload)
            if resp.status_code in (400, 403):
                data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                return f"Cannot submit quiz: {data.get('message', resp.text)}"
            resp.raise_for_status()

            data = resp.json()
            result_lines = [f"Quiz {quiz_id} submitted."]
            if isinstance(data, dict):
                if "results" in data:
                    r = data["results"]
                    result_lines.append(f"  Score: {r.get('result', 'N/A')}%")
                    result_lines.append(f"  Status: {r.get('grade', 'N/A')}")
                elif "message" in data:
                    result_lines.append(f"  {data['message']}")
            return "\n".join(result_lines)

    @mcp.tool()
    async def lp_finish_lesson(
        lesson_id: int,
        context=None,
    ) -> str:
        """Mark a lesson as complete.

        Args:
            lesson_id: The lesson post ID
        """
        connection_id, user_id = get_connection_info(context)

        async with await _get_lp_client(connection_id, user_id) as client:
            resp = await client.post("/lessons/finish", json={"id": lesson_id})
            if resp.status_code in (400, 403):
                data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                return f"Cannot finish lesson: {data.get('message', resp.text)}"
            resp.raise_for_status()

            return f"Lesson {lesson_id} marked as complete."
