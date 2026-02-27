"use client";

import { useState, useEffect, useCallback } from "react";
import { useConnections } from "@/contexts/connection-context";
import { useAuth } from "@/contexts/auth-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useToast } from "@/hooks/use-toast";
import {
  GraduationCap,
  Search,
  BookOpen,
  ClipboardList,
  Users,
  Clock,
  ChevronRight,
  ChevronDown,
  RefreshCw,
  AlertCircle,
  PlayCircle,
  CheckCircle2,
  FileQuestion,
} from "lucide-react";

interface Course {
  id: number;
  title: { rendered: string } | string;
  status: string;
  content?: { rendered: string } | string;
  excerpt?: { rendered: string } | string;
  price?: string;
  count_students?: number;
  duration?: string;
  sections?: Section[];
}

interface Section {
  title: string;
  items: SectionItem[];
}

interface SectionItem {
  id: number;
  title: string;
  type: string;
}

interface Quiz {
  id: number;
  title: { rendered: string } | string;
  status: string;
  duration?: string;
  passing_grade?: string;
  questions?: QuizQuestion[];
}

interface QuizQuestion {
  title: string;
  type: string;
}

function getTitle(t: { rendered: string } | string | undefined): string {
  if (!t) return "Untitled";
  if (typeof t === "string") return t;
  return t.rendered || "Untitled";
}

function stripHtml(html: string): string {
  return html.replace(/<[^>]*>/g, "").trim();
}

export default function CoursesPage() {
  const { activeConnection } = useConnections();
  const { isAuthenticated } = useAuth();
  const { toast } = useToast();

  const [courses, setCourses] = useState<Course[]>([]);
  const [quizzes, setQuizzes] = useState<Quiz[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [lpInstalled, setLpInstalled] = useState<boolean | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeTab, setActiveTab] = useState<"courses" | "quizzes">("courses");

  // Course detail dialog
  const [selectedCourse, setSelectedCourse] = useState<Course | null>(null);
  const [courseDetailOpen, setCourseDetailOpen] = useState(false);
  const [courseDetailLoading, setCourseDetailLoading] = useState(false);

  // Quiz detail dialog
  const [selectedQuiz, setSelectedQuiz] = useState<Quiz | null>(null);
  const [quizDetailOpen, setQuizDetailOpen] = useState(false);
  const [quizDetailLoading, setQuizDetailLoading] = useState(false);

  const connectionId = activeConnection?.id;

  const fetchCourses = useCallback(async () => {
    if (!connectionId) return;
    setIsLoading(true);
    try {
      const params = new URLSearchParams({ per_page: "50" });
      if (searchQuery) params.set("search", searchQuery);

      const resp = await fetch(
        `/api/connections/${connectionId}/learnpress/courses?${params}`
      );
      const data = await resp.json();

      if (data.learnpress_installed === false) {
        setLpInstalled(false);
        setCourses([]);
      } else {
        setLpInstalled(true);
        setCourses(data.courses || []);
      }
    } catch {
      toast({
        title: "Error",
        description: "Failed to fetch courses",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  }, [connectionId, searchQuery, toast]);

  const fetchQuizzes = useCallback(async () => {
    if (!connectionId) return;
    try {
      const resp = await fetch(
        `/api/connections/${connectionId}/learnpress/quizzes?per_page=50`
      );
      const data = await resp.json();
      setQuizzes(data.quizzes || []);
    } catch {
      // silent
    }
  }, [connectionId]);

  useEffect(() => {
    if (connectionId && isAuthenticated) {
      fetchCourses();
      fetchQuizzes();
    }
  }, [connectionId, isAuthenticated, fetchCourses, fetchQuizzes]);

  const openCourseDetail = async (course: Course) => {
    if (!connectionId) return;
    setCourseDetailOpen(true);
    setCourseDetailLoading(true);
    setSelectedCourse(course);

    try {
      const resp = await fetch(
        `/api/connections/${connectionId}/learnpress/courses/${course.id}`
      );
      const data = await resp.json();
      if (data && !data.error) {
        setSelectedCourse(data);
      }
    } catch {
      // keep the basic course data
    } finally {
      setCourseDetailLoading(false);
    }
  };

  const openQuizDetail = async (quiz: Quiz) => {
    if (!connectionId) return;
    setQuizDetailOpen(true);
    setQuizDetailLoading(true);
    setSelectedQuiz(quiz);

    try {
      const resp = await fetch(
        `/api/connections/${connectionId}/learnpress/quizzes/${quiz.id}`
      );
      const data = await resp.json();
      if (data && !data.error) {
        setSelectedQuiz(data);
      }
    } catch {
      // keep basic quiz data
    } finally {
      setQuizDetailLoading(false);
    }
  };

  const handleEnroll = async (courseId: number) => {
    if (!connectionId) return;
    try {
      const resp = await fetch(
        `/api/connections/${connectionId}/learnpress/courses/${courseId}/enroll`,
        { method: "POST" }
      );
      const data = await resp.json();
      if (data.success) {
        toast({ title: "Enrolled", description: "Successfully enrolled in course" });
      } else {
        toast({
          title: "Enrollment failed",
          description: data.error || "Could not enroll",
          variant: "destructive",
        });
      }
    } catch {
      toast({
        title: "Error",
        description: "Failed to enroll",
        variant: "destructive",
      });
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="container mx-auto py-8 px-4">
        <p className="text-muted-foreground">Please sign in to view courses.</p>
      </div>
    );
  }

  if (!activeConnection) {
    return (
      <div className="container mx-auto py-8 px-4">
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight">Courses</h1>
          <p className="text-muted-foreground mt-2">
            LearnPress LMS course management
          </p>
        </div>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-yellow-500" />
              No active connection
            </CardTitle>
            <CardDescription>
              Activate a WordPress connection to manage LearnPress courses.
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  if (lpInstalled === false) {
    return (
      <div className="container mx-auto py-8 px-4">
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight">Courses</h1>
          <p className="text-muted-foreground mt-2">
            LearnPress LMS course management
          </p>
        </div>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <GraduationCap className="h-5 w-5" />
              LearnPress Not Installed
            </CardTitle>
            <CardDescription>
              LearnPress is not detected on &quot;{activeConnection.name}&quot;.
              Install it from the Connections page to manage courses.
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 px-4">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Courses</h1>
          <p className="text-muted-foreground mt-2">
            LearnPress LMS on {activeConnection.name}
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            fetchCourses();
            fetchQuizzes();
          }}
          disabled={isLoading}
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6">
        <Button
          variant={activeTab === "courses" ? "default" : "outline"}
          size="sm"
          onClick={() => setActiveTab("courses")}
        >
          <BookOpen className="h-4 w-4 mr-2" />
          Courses ({courses.length})
        </Button>
        <Button
          variant={activeTab === "quizzes" ? "default" : "outline"}
          size="sm"
          onClick={() => setActiveTab("quizzes")}
        >
          <ClipboardList className="h-4 w-4 mr-2" />
          Quizzes ({quizzes.length})
        </Button>
      </div>

      {/* Search */}
      {activeTab === "courses" && (
        <div className="relative mb-6 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search courses..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && fetchCourses()}
            className="pl-10"
          />
        </div>
      )}

      {/* Courses tab */}
      {activeTab === "courses" && (
        <>
          {isLoading ? (
            <div className="text-muted-foreground py-8 text-center">
              Loading courses...
            </div>
          ) : courses.length === 0 ? (
            <Card>
              <CardHeader>
                <CardTitle>No courses found</CardTitle>
                <CardDescription>
                  {searchQuery
                    ? "No courses match your search."
                    : "No courses on this site yet. Create one in wp-admin or via the MCP tools."}
                </CardDescription>
              </CardHeader>
            </Card>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {courses.map((course) => (
                <Card
                  key={course.id}
                  className="cursor-pointer hover:border-primary/50 transition-colors"
                  onClick={() => openCourseDetail(course)}
                >
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between gap-2">
                      <CardTitle className="text-lg leading-snug">
                        {getTitle(course.title)}
                      </CardTitle>
                      <span
                        className={`shrink-0 text-xs px-2 py-0.5 rounded-full font-medium ${
                          course.status === "publish"
                            ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                            : "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400"
                        }`}
                      >
                        {course.status}
                      </span>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      {course.count_students != null && (
                        <span className="flex items-center gap-1">
                          <Users className="h-3.5 w-3.5" />
                          {course.count_students}
                        </span>
                      )}
                      {course.duration && (
                        <span className="flex items-center gap-1">
                          <Clock className="h-3.5 w-3.5" />
                          {course.duration}
                        </span>
                      )}
                      {course.price && (
                        <span className="font-medium text-foreground">
                          {course.price === "0" || course.price === "" ? "Free" : `$${course.price}`}
                        </span>
                      )}
                    </div>
                    <div className="mt-3 flex items-center text-xs text-muted-foreground">
                      <ChevronRight className="h-3.5 w-3.5 mr-1" />
                      Click for details
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </>
      )}

      {/* Quizzes tab */}
      {activeTab === "quizzes" && (
        <>
          {quizzes.length === 0 ? (
            <Card>
              <CardHeader>
                <CardTitle>No quizzes found</CardTitle>
                <CardDescription>
                  No quizzes on this site yet.
                </CardDescription>
              </CardHeader>
            </Card>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {quizzes.map((quiz) => (
                <Card
                  key={quiz.id}
                  className="cursor-pointer hover:border-primary/50 transition-colors"
                  onClick={() => openQuizDetail(quiz)}
                >
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between gap-2">
                      <CardTitle className="text-lg leading-snug">
                        {getTitle(quiz.title)}
                      </CardTitle>
                      <span
                        className={`shrink-0 text-xs px-2 py-0.5 rounded-full font-medium ${
                          quiz.status === "publish"
                            ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                            : "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400"
                        }`}
                      >
                        {quiz.status}
                      </span>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      {quiz.duration && (
                        <span className="flex items-center gap-1">
                          <Clock className="h-3.5 w-3.5" />
                          {quiz.duration}
                        </span>
                      )}
                      {quiz.passing_grade && (
                        <span>Pass: {quiz.passing_grade}%</span>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </>
      )}

      {/* Course Detail Dialog */}
      <Dialog open={courseDetailOpen} onOpenChange={setCourseDetailOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <BookOpen className="h-5 w-5" />
              {selectedCourse ? getTitle(selectedCourse.title) : "Course"}
            </DialogTitle>
          </DialogHeader>

          {courseDetailLoading ? (
            <div className="py-8 text-center text-muted-foreground">
              Loading course details...
            </div>
          ) : selectedCourse ? (
            <div className="space-y-6">
              {/* Meta row */}
              <div className="flex flex-wrap gap-4 text-sm">
                <span className="flex items-center gap-1">
                  <span className="font-medium">ID:</span> {selectedCourse.id}
                </span>
                <span className="flex items-center gap-1">
                  <span className="font-medium">Status:</span>{" "}
                  <span
                    className={`px-2 py-0.5 rounded-full text-xs ${
                      selectedCourse.status === "publish"
                        ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                        : "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400"
                    }`}
                  >
                    {selectedCourse.status}
                  </span>
                </span>
                {selectedCourse.count_students != null && (
                  <span className="flex items-center gap-1">
                    <Users className="h-4 w-4" />
                    {selectedCourse.count_students} students
                  </span>
                )}
                {selectedCourse.duration && (
                  <span className="flex items-center gap-1">
                    <Clock className="h-4 w-4" />
                    {selectedCourse.duration}
                  </span>
                )}
                {selectedCourse.price && (
                  <span className="font-medium">
                    {selectedCourse.price === "0" || selectedCourse.price === ""
                      ? "Free"
                      : `$${selectedCourse.price}`}
                  </span>
                )}
              </div>

              {/* Description */}
              {selectedCourse.content && (
                <div>
                  <h3 className="font-semibold mb-2">Description</h3>
                  <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                    {stripHtml(
                      typeof selectedCourse.content === "string"
                        ? selectedCourse.content
                        : selectedCourse.content.rendered || ""
                    ).slice(0, 500)}
                  </p>
                </div>
              )}

              {/* Curriculum */}
              {selectedCourse.sections && selectedCourse.sections.length > 0 && (
                <div>
                  <h3 className="font-semibold mb-3">
                    Curriculum ({selectedCourse.sections.length} sections)
                  </h3>
                  <div className="space-y-3">
                    {selectedCourse.sections.map((section, idx) => (
                      <CurriculumSection key={idx} section={section} />
                    ))}
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-2 pt-2">
                <Button
                  size="sm"
                  onClick={() => handleEnroll(selectedCourse.id)}
                >
                  <PlayCircle className="h-4 w-4 mr-2" />
                  Enroll
                </Button>
              </div>
            </div>
          ) : null}
        </DialogContent>
      </Dialog>

      {/* Quiz Detail Dialog */}
      <Dialog open={quizDetailOpen} onOpenChange={setQuizDetailOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <ClipboardList className="h-5 w-5" />
              {selectedQuiz ? getTitle(selectedQuiz.title) : "Quiz"}
            </DialogTitle>
          </DialogHeader>

          {quizDetailLoading ? (
            <div className="py-8 text-center text-muted-foreground">
              Loading quiz details...
            </div>
          ) : selectedQuiz ? (
            <div className="space-y-6">
              <div className="flex flex-wrap gap-4 text-sm">
                <span>
                  <span className="font-medium">ID:</span> {selectedQuiz.id}
                </span>
                <span>
                  <span className="font-medium">Status:</span>{" "}
                  <span
                    className={`px-2 py-0.5 rounded-full text-xs ${
                      selectedQuiz.status === "publish"
                        ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                        : "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400"
                    }`}
                  >
                    {selectedQuiz.status}
                  </span>
                </span>
                {selectedQuiz.duration && (
                  <span className="flex items-center gap-1">
                    <Clock className="h-4 w-4" />
                    {selectedQuiz.duration}
                  </span>
                )}
                {selectedQuiz.passing_grade && (
                  <span>
                    <span className="font-medium">Passing grade:</span>{" "}
                    {selectedQuiz.passing_grade}%
                  </span>
                )}
              </div>

              {selectedQuiz.questions && selectedQuiz.questions.length > 0 && (
                <div>
                  <h3 className="font-semibold mb-3">
                    Questions ({selectedQuiz.questions.length})
                  </h3>
                  <div className="space-y-2">
                    {selectedQuiz.questions.map((q, idx) => (
                      <div
                        key={idx}
                        className="flex items-center gap-3 p-2 rounded-md bg-muted/50"
                      >
                        <FileQuestion className="h-4 w-4 shrink-0 text-muted-foreground" />
                        <span className="text-sm">{q.title}</span>
                        <span className="ml-auto text-xs text-muted-foreground px-2 py-0.5 bg-muted rounded">
                          {q.type}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  );
}

function CurriculumSection({ section }: { section: Section }) {
  const [open, setOpen] = useState(true);

  return (
    <div className="border rounded-lg overflow-hidden">
      <button
        className="w-full flex items-center gap-2 p-3 text-left font-medium text-sm hover:bg-muted/50"
        onClick={() => setOpen(!open)}
      >
        {open ? (
          <ChevronDown className="h-4 w-4 shrink-0" />
        ) : (
          <ChevronRight className="h-4 w-4 shrink-0" />
        )}
        {section.title}
        <span className="ml-auto text-xs text-muted-foreground">
          {section.items.length} items
        </span>
      </button>
      {open && section.items.length > 0 && (
        <div className="border-t divide-y">
          {section.items.map((item) => (
            <div
              key={item.id}
              className="flex items-center gap-3 px-4 py-2 text-sm"
            >
              {item.type === "quiz" ? (
                <ClipboardList className="h-4 w-4 shrink-0 text-orange-500" />
              ) : (
                <CheckCircle2 className="h-4 w-4 shrink-0 text-blue-500" />
              )}
              <span>{item.title}</span>
              <span className="ml-auto text-xs text-muted-foreground">
                {item.type}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
