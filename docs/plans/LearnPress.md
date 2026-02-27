# LearnPress Integration Analysis

> Investigation document for integrating LearnPress LMS into the Articulate multi-tenant WordPress platform.
> No active implementation yet -- research and planning only.

## What LearnPress Is

**LearnPress** is a free, open-source WordPress LMS plugin (ThimPress). Most popular WordPress LMS on WordPress.org. Current version: 4.3.1 (Nov 2025), with beta OpenAI support for AI-generated course content in 4.3.0.

### Core Features

- Course builder with sections, lessons, and quizzes
- Quiz engine (multiple choice, true/false, fill-in-the-blank, etc.)
- Student enrollment, progress tracking, completion
- Payment/order system (paid and free courses)
- User roles: Instructor (`lp_teacher`) and Student (standard `subscriber`)
- Premium add-ons: Certificates ($39.99), Gradebook ($39.99), Assignments ($39.99), Content Drip, Reviews, Wishlists
- Pro Bundle: $249.99 for all add-ons

### Data Model

**5 custom post types** (stored in `wp_posts`):

| Post Type | Purpose |
|-----------|---------|
| `lp_course` | Courses (top-level container) |
| `lp_lesson` | Lessons within course sections |
| `lp_quiz` | Quizzes within course sections |
| `lp_question` | Individual quiz questions |
| `lp_order` | Purchase/enrollment orders |

**8+ custom database tables** (per WordPress instance):

| Table | Purpose |
|-------|---------|
| `{prefix}_learnpress_sections` | Course curriculum sections |
| `{prefix}_learnpress_section_items` | Maps lessons/quizzes to sections |
| `{prefix}_learnpress_user_items` | User enrollment and progress |
| `{prefix}_learnpress_user_itemmeta` | Progress metadata |
| `{prefix}_learnpress_user_item_results` | Quiz/course completion results |
| `{prefix}_learnpress_quiz_questions` | Quiz-to-question relationships |
| `{prefix}_learnpress_question_answers` | Answer options for questions |
| `{prefix}_learnpress_order_items` | Items within an order |
| `{prefix}_learnpress_order_itemmeta` | Order item metadata |

**Custom taxonomy**: `course_category`

---

## REST API

LearnPress exposes two namespaces: `learnpress/v1` and `lp/v1`. Authentication uses standard WordPress methods (Application Passwords, which Articulate already stores per-connection).

### Courses

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/learnpress/v1/courses` | List courses (search, category, pagination) |
| GET | `/learnpress/v1/courses/{id}` | Get course details + curriculum |
| GET | `/learnpress/v1/courses/?learned=true` | List enrolled courses for current user |
| POST | `/learnpress/v1/courses/enroll` | Enroll in a course |
| POST | `/learnpress/v1/courses/finish` | Complete a course |
| POST | `/learnpress/v1/courses/retake` | Retake a course |
| GET | `/lp/v1/courses/archive-course` | Admin: list courses with filters |
| POST | `/lp/v1/courses/purchase-course` | Purchase a course |

### Lessons

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/learnpress/v1/lessons` | List lessons |
| GET | `/learnpress/v1/lessons/{id}` | Get lesson details |
| POST | `/learnpress/v1/lessons/finish` | Mark lesson complete |

### Quizzes

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/learnpress/v1/quiz` | List quizzes |
| GET | `/learnpress/v1/quiz/{id}` | Get quiz with questions |
| POST | `/learnpress/v1/quiz/start` | Start quiz attempt |
| POST | `/learnpress/v1/quiz/check_answer` | Check answer mid-quiz |
| POST | `/learnpress/v1/quiz/finish` | Submit/finish quiz |

### Users & Profiles

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/learnpress/v1/users/` | List LMS users |
| GET | `/lp/v1/profile/student/statistic` | Student stats |
| GET | `/lp/v1/profile/instructor/statistic` | Instructor stats |

### Orders

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/lp/v1/admin/orders` | List orders (admin) |
| POST | `/lp/v1/orders/verify-payment` | Verify payment |
| POST | `/lp/v1/orders/cancel` | Cancel order |

### Assignments (add-on required)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/learnpress/v1/assignments/` | List assignments |
| GET | `/learnpress/v1/assignments/{id}` | Get assignment |
| POST | `/learnpress/v1/assignments/start/` | Start assignment |
| POST | `/learnpress/v1/assignments/submit/` | Submit assignment (with file) |

### Materials

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/lp/v1/material/upload` | Upload course material |
| GET | `/lp/v1/material/download` | Download material |
| DELETE | `/lp/v1/material/delete` | Delete material |

### Admin

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/lp/v1/admin/courses` | Admin course list |
| GET | `/lp/v1/admin/users` | Admin user list |
| GET/PUT | `/lp/v1/admin/settings` | Get/update settings |

### Error Format

```json
{"code": "error_code", "message": "Error message", "data": {"status": 400}}
```

Rate limit: 100 requests/minute/IP.

---

## WPGraphQL Compatibility

**No official WPGraphQL extension exists for LearnPress.** This is a significant finding.

### Bridge Mu-Plugin

LearnPress post types are not registered with `show_in_graphql`. A small mu-plugin can expose them:

```php
// mu-plugins/learnpress-wpgraphql.php
add_filter('register_post_type_args', function($args, $post_type) {
    $lp_types = [
        'lp_course'   => ['single' => 'LpCourse',   'plural' => 'LpCourses'],
        'lp_lesson'   => ['single' => 'LpLesson',   'plural' => 'LpLessons'],
        'lp_quiz'     => ['single' => 'LpQuiz',     'plural' => 'LpQuizzes'],
        'lp_question' => ['single' => 'LpQuestion',  'plural' => 'LpQuestions'],
        'lp_order'    => ['single' => 'LpOrder',     'plural' => 'LpOrders'],
    ];
    if (isset($lp_types[$post_type])) {
        $args['show_in_graphql']     = true;
        $args['graphql_single_name'] = $lp_types[$post_type]['single'];
        $args['graphql_plural_name'] = $lp_types[$post_type]['plural'];
    }
    return $args;
}, 10, 2);

add_filter('register_taxonomy_args', function($args, $taxonomy) {
    if ($taxonomy === 'course_category') {
        $args['show_in_graphql']     = true;
        $args['graphql_single_name'] = 'CourseCategory';
        $args['graphql_plural_name'] = 'CourseCategories';
    }
    return $args;
}, 10, 2);
```

### Limitation

GraphQL would only expose raw post data (title, content, meta). Relational data in custom tables (sections, progress, quiz questions, answers, orders) is **not accessible** through WPGraphQL without custom resolvers.

### Recommended: Hybrid Approach

- **WPGraphQL** for basic content listing (courses, lessons, quizzes as post types)
- **LearnPress REST API** for LMS operations (enrollment, quiz attempts, progress, orders, grading)

This matches the existing `check_learnpress_endpoint` which tries GraphQL first, then falls back to REST.

---

## Current State in Codebase

Already implemented (by Copilot):

| File | Purpose |
|------|---------|
| `mcp-server/src/articulate_mcp/routes/learnpress.py` | Check if installed + install endpoint |
| `web/src/app/api/connections/[id]/learnpress/check/route.ts` | Next.js proxy for check |
| `web/src/app/api/connections/[id]/learnpress/install/route.ts` | Next.js proxy for install |
| `web/src/app/connections/page.tsx` | "Install LearnPress" button on connection cards |
| `scripts/setup-remote-wordpress.py` | SSH plugin install with `--plugins learnpress` |

---

## Integration Plan

### Phase 1: MCP Tools for Course Management

Create `mcp-server/src/articulate_mcp/tools/learnpress.py`:

| Tool | Description | API Endpoint |
|------|-------------|--------------|
| `lp_list_courses` | List courses with filters | `GET /learnpress/v1/courses` |
| `lp_get_course` | Course details + curriculum | `GET /learnpress/v1/courses/{id}` |
| `lp_create_course` | Create new course | `POST /wp/v2/lp_course` |
| `lp_update_course` | Update course | `PUT /wp/v2/lp_course/{id}` |
| `lp_delete_course` | Delete course | `DELETE /wp/v2/lp_course/{id}` |
| `lp_list_lessons` | List lessons | `GET /learnpress/v1/lessons` |
| `lp_get_lesson` | Lesson details | `GET /learnpress/v1/lessons/{id}` |
| `lp_create_lesson` | Create lesson | `POST /wp/v2/lp_lesson` |
| `lp_list_quizzes` | List quizzes | `GET /learnpress/v1/quiz` |
| `lp_get_quiz` | Quiz with questions | `GET /learnpress/v1/quiz/{id}` |
| `lp_create_quiz` | Create quiz | `POST /wp/v2/lp_quiz` |

### Phase 2: Student Enrollment & Progress

| Tool | Description | API Endpoint |
|------|-------------|--------------|
| `lp_enroll_student` | Enroll user | `POST /learnpress/v1/courses/enroll` |
| `lp_get_student_progress` | Progress stats | `GET /lp/v1/profile/student/statistic` |
| `lp_finish_course` | Mark complete | `POST /learnpress/v1/courses/finish` |
| `lp_retake_course` | Allow retake | `POST /learnpress/v1/courses/retake` |
| `lp_list_enrolled_courses` | Enrolled courses | `GET /learnpress/v1/courses/?learned=true` |
| `lp_start_quiz` | Start quiz | `POST /learnpress/v1/quiz/start` |
| `lp_submit_quiz` | Submit quiz | `POST /learnpress/v1/quiz/finish` |

### Phase 3: REST Routes + Next.js Frontend

**Starlette routes** (proxied by Next.js API routes):

```
GET  /connections/{id}/learnpress/courses
GET  /connections/{id}/learnpress/courses/{course_id}
POST /connections/{id}/learnpress/courses/{course_id}/enroll
GET  /connections/{id}/learnpress/courses/{course_id}/students
GET  /connections/{id}/learnpress/quizzes
GET  /connections/{id}/learnpress/quizzes/{quiz_id}
GET  /connections/{id}/learnpress/orders
GET  /connections/{id}/learnpress/student/progress
```

**Frontend pages**:
- Course dashboard (grid/list with filters)
- Course detail/builder (curriculum, students, settings tabs)
- Quiz builder (question list, editor, settings)
- Student progress view (enrolled courses, grades, completion)

### Phase 4: Future TODO

- [ ] Grade reporting (requires Gradebook add-on, $39.99)
- [ ] Grade export to CSV/PDF
- [ ] Certificate management (requires Certificates add-on, $39.99)
- [ ] Certificate templates via MCP
- [ ] Automated certificate issuance on completion
- [ ] Payment/order management dashboard
- [ ] Stripe gateway configuration per tenant
- [ ] Coupon code management
- [ ] Revenue reporting per course/instructor/tenant
- [ ] Content Drip scheduling (time-release lessons)
- [ ] Prerequisites management
- [ ] Assignment workflow (requires Assignment add-on, $39.99)
- [ ] Course reviews and ratings
- [ ] Instructor analytics
- [ ] Course cloning across tenants
- [ ] AI course content generation (LearnPress 4.3 OpenAI integration)
- [ ] SCORM/xAPI compliance
- [ ] Bulk course import/export
- [ ] Real-time notifications (WebSocket) for quiz/enrollment events

### Infrastructure TODO

- [ ] Add LearnPress REST API health check to `/health/deep`
- [ ] Cache LearnPress API responses in Redis
- [ ] Add `lp_teacher` role to WordPress role sync mapping
- [ ] Create LearnPress-specific capability checks (`edit_lp_courses`, etc.)
- [ ] Handle API rate limits (retry with backoff on 429)
- [ ] Deploy WPGraphQL bridge mu-plugin to tenant WordPress instances
- [ ] Add LearnPress to default plugin list in tenant provisioning template

---

## Role Mapping

| Articulate Role | WordPress Role | LearnPress Capability |
|----------------|----------------|----------------------|
| Owner | administrator | Full LMS control |
| Admin | administrator | Full LMS control |
| Editor/Instructor | lp_teacher | Create/manage own courses |
| Viewer/Student | subscriber | Enroll, take courses |

---

## Multi-Tenant Considerations

- LearnPress data is naturally scoped per WordPress instance (Level 2 isolation)
- Each tenant gets its own LearnPress installation with separate DB tables
- Authentication uses per-connection WordPress Application Passwords (already stored)
- Plugin installation already automated via `--plugins learnpress` flag
- No shared-instance (Level 1) LMS support recommended -- data isolation too weak

---

## Sources

- [LearnPress REST API Complete List](https://learnpresslms.com/blog/a-complete-list-of-the-learnpress-rest-api/)
- [LearnPress API Reference](https://docs.thimpress.com/learnpress-developer-documentation/api-reference/)
- [LearnPress Database Structure](https://learnpresslms.com/docs/learnpress-developer-documentation/architecture-core-concepts/database-structure/)
- [LearnPress GitHub](https://github.com/LearnPress/learnpress)
- [WPGraphQL Custom Post Types](https://www.wpgraphql.com/docs/custom-post-types)
- [LearnPress Add-ons](https://learnpresslms.com/add-ons/)
- [LearnPress Pro Bundle](https://thimpress.com/product/learnpress-pro/) ($249.99)
