"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/use-toast";
import {
  Sparkles,
  Loader2,
  CheckCircle2,
  AlertCircle,
  TrendingUp,
  BookOpen,
  FileText,
  Search,
  Heart,
  Wand2,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";

interface ContentAssistantSidebarProps {
  content: string;
  onContentChange?: (content: string) => void;
}

interface ToneAnalysis {
  current_tone: string;
  matches_target: boolean;
  suggestions: string[];
}

interface ReadabilityAnalysis {
  grade_level: string;
  score: number;
  suggestions: string[];
}

interface GrammarAnalysis {
  errors_found: number;
  issues: Array<{
    text: string;
    suggestion: string;
    type: string;
  }>;
}

interface SEOAnalysis {
  score: number;
  keywords: string[];
  suggestions: string[];
}

interface EngagementAnalysis {
  score: number;
  strengths: string[];
  improvements: string[];
}

interface Analyses {
  tone?: ToneAnalysis;
  readability?: ReadabilityAnalysis;
  grammar?: GrammarAnalysis;
  seo?: SEOAnalysis;
  engagement?: EngagementAnalysis;
}

export function ContentAssistantSidebar({
  content,
  onContentChange,
}: ContentAssistantSidebarProps) {
  const { toast } = useToast();
  const [analyzing, setAnalyzing] = useState(false);
  const [improving, setImproving] = useState(false);
  const [analyses, setAnalyses] = useState<Analyses>({});
  const [improvedContent, setImprovedContent] = useState("");
  const [changesSummary, setChangesSummary] = useState("");
  const [selectedImprovementType, setSelectedImprovementType] =
    useState("clarity");

  async function analyzeContent(types: string[]) {
    if (!content.trim()) {
      toast({
        title: "No content",
        description: "Please enter some content to analyze",
        variant: "destructive",
      });
      return;
    }

    setAnalyzing(true);
    setAnalyses({});

    try {
      const sessionId = localStorage.getItem("sessionId");
      if (!sessionId) throw new Error("Not logged in");

      const response = await fetch("http://localhost:8000/ai/analyze-content", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-ID": sessionId,
        },
        body: JSON.stringify({
          content,
          analysis_types: types,
        }),
      });

      if (!response.ok) throw new Error("Failed to analyze content");

      const data = await response.json();
      setAnalyses(data.analyses || {});

      toast({
        title: "Analysis complete",
        description: `Analyzed ${types.length} aspect${types.length > 1 ? "s" : ""} of your content`,
      });
    } catch (error) {
      toast({
        title: "Analysis failed",
        description: error instanceof Error ? error.message : "Unknown error",
        variant: "destructive",
      });
    } finally {
      setAnalyzing(false);
    }
  }

  async function improveContent(improvementType: string) {
    if (!content.trim()) {
      toast({
        title: "No content",
        description: "Please enter some content to improve",
        variant: "destructive",
      });
      return;
    }

    setImproving(true);
    setImprovedContent("");
    setChangesSummary("");

    try {
      const sessionId = localStorage.getItem("sessionId");
      if (!sessionId) throw new Error("Not logged in");

      const response = await fetch("http://localhost:8000/ai/improve-content", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-ID": sessionId,
        },
        body: JSON.stringify({
          content,
          improvement_type: improvementType,
        }),
      });

      if (!response.ok) throw new Error("Failed to improve content");

      const data = await response.json();
      setImprovedContent(data.improved_content || "");
      setChangesSummary(data.changes || "");

      toast({
        title: "Content improved",
        description: "AI has generated an improved version",
      });
    } catch (error) {
      toast({
        title: "Improvement failed",
        description: error instanceof Error ? error.message : "Unknown error",
        variant: "destructive",
      });
    } finally {
      setImproving(false);
    }
  }

  function applyImprovedContent() {
    if (improvedContent && onContentChange) {
      onContentChange(improvedContent);
      toast({
        title: "Content applied",
        description: "Improved content has been applied to the editor",
      });
    }
  }

  function getScoreColor(score: number): string {
    if (score >= 8) return "text-green-600";
    if (score >= 5) return "text-amber-600";
    return "text-red-600";
  }

  function getScoreBadgeVariant(
    score: number
  ): "default" | "secondary" | "destructive" {
    if (score >= 8) return "default";
    if (score >= 5) return "secondary";
    return "destructive";
  }

  return (
    <div className="h-full flex flex-col">
      <div className="p-4 border-b">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <Wand2 className="h-5 w-5" />
          Content Assistant
        </h2>
        <p className="text-sm text-muted-foreground mt-1">
          AI-powered analysis and improvements
        </p>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-4 space-y-4">
          <Tabs defaultValue="analyze" className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="analyze">Analyze</TabsTrigger>
              <TabsTrigger value="improve">Improve</TabsTrigger>
            </TabsList>

            <TabsContent value="analyze" className="space-y-4">
              <div className="space-y-2">
                <Label>Select analysis types</Label>
                <div className="grid grid-cols-2 gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => analyzeContent(["tone"])}
                    disabled={analyzing}
                    className="justify-start"
                  >
                    <Heart className="h-3 w-3 mr-2" />
                    Tone
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => analyzeContent(["readability"])}
                    disabled={analyzing}
                    className="justify-start"
                  >
                    <BookOpen className="h-3 w-3 mr-2" />
                    Readability
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => analyzeContent(["grammar"])}
                    disabled={analyzing}
                    className="justify-start"
                  >
                    <FileText className="h-3 w-3 mr-2" />
                    Grammar
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => analyzeContent(["seo"])}
                    disabled={analyzing}
                    className="justify-start"
                  >
                    <Search className="h-3 w-3 mr-2" />
                    SEO
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => analyzeContent(["engagement"])}
                    disabled={analyzing}
                    className="justify-start"
                  >
                    <TrendingUp className="h-3 w-3 mr-2" />
                    Engagement
                  </Button>
                </div>
                <Button
                  onClick={() =>
                    analyzeContent([
                      "tone",
                      "readability",
                      "grammar",
                      "seo",
                      "engagement",
                    ])
                  }
                  disabled={analyzing}
                  className="w-full"
                >
                  {analyzing ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Analyzing...
                    </>
                  ) : (
                    <>
                      <Sparkles className="h-4 w-4 mr-2" />
                      Analyze All
                    </>
                  )}
                </Button>
              </div>

              {/* Analysis Results */}
              {analyses.tone && (
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <Heart className="h-4 w-4" />
                      Tone Analysis
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">Current:</span>
                      <Badge variant="secondary">
                        {analyses.tone.current_tone}
                      </Badge>
                      {analyses.tone.matches_target && (
                        <CheckCircle2 className="h-4 w-4 text-green-600" />
                      )}
                    </div>
                    {analyses.tone.suggestions.length > 0 && (
                      <div className="space-y-1">
                        <span className="text-xs font-medium">
                          Suggestions:
                        </span>
                        <ul className="text-xs space-y-1">
                          {analyses.tone.suggestions.map((suggestion, i) => (
                            <li key={i} className="flex items-start gap-2">
                              <span className="text-muted-foreground">•</span>
                              <span>{suggestion}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}

              {analyses.readability && (
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <BookOpen className="h-4 w-4" />
                      Readability
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Reading Level:</span>
                      <Badge variant="secondary">
                        {analyses.readability.grade_level}
                      </Badge>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Score:</span>
                      <span
                        className={`text-sm font-bold ${getScoreColor(analyses.readability.score)}`}
                      >
                        {analyses.readability.score}/10
                      </span>
                    </div>
                    {analyses.readability.suggestions.length > 0 && (
                      <div className="space-y-1">
                        <span className="text-xs font-medium">
                          Suggestions:
                        </span>
                        <ul className="text-xs space-y-1">
                          {analyses.readability.suggestions.map(
                            (suggestion, i) => (
                              <li key={i} className="flex items-start gap-2">
                                <span className="text-muted-foreground">•</span>
                                <span>{suggestion}</span>
                              </li>
                            )
                          )}
                        </ul>
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}

              {analyses.grammar && (
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <FileText className="h-4 w-4" />
                      Grammar & Spelling
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Issues Found:</span>
                      <Badge
                        variant={
                          analyses.grammar.errors_found === 0
                            ? "default"
                            : "destructive"
                        }
                      >
                        {analyses.grammar.errors_found}
                      </Badge>
                    </div>
                    {analyses.grammar.issues.length > 0 && (
                      <div className="space-y-2">
                        {analyses.grammar.issues.map((issue, i) => (
                          <div
                            key={i}
                            className="p-2 border rounded-md space-y-1"
                          >
                            <div className="flex items-start gap-2">
                              <AlertCircle className="h-3 w-3 text-red-600 mt-0.5" />
                              <div className="flex-1 space-y-1">
                                <p className="text-xs font-mono bg-muted px-1 rounded">
                                  {issue.text}
                                </p>
                                <p className="text-xs text-muted-foreground">
                                  {issue.type}
                                </p>
                                <p className="text-xs">
                                  <span className="font-medium">Fix:</span>{" "}
                                  {issue.suggestion}
                                </p>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}

              {analyses.seo && (
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <Search className="h-4 w-4" />
                      SEO Analysis
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm">SEO Score:</span>
                      <span
                        className={`text-sm font-bold ${getScoreColor(analyses.seo.score)}`}
                      >
                        {analyses.seo.score}/10
                      </span>
                    </div>
                    {analyses.seo.keywords.length > 0 && (
                      <div className="space-y-1">
                        <span className="text-xs font-medium">Keywords:</span>
                        <div className="flex flex-wrap gap-1">
                          {analyses.seo.keywords.map((keyword, i) => (
                            <Badge key={i} variant="outline" className="text-xs">
                              {keyword}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}
                    {analyses.seo.suggestions.length > 0 && (
                      <div className="space-y-1">
                        <span className="text-xs font-medium">
                          Suggestions:
                        </span>
                        <ul className="text-xs space-y-1">
                          {analyses.seo.suggestions.map((suggestion, i) => (
                            <li key={i} className="flex items-start gap-2">
                              <span className="text-muted-foreground">•</span>
                              <span>{suggestion}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}

              {analyses.engagement && (
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <TrendingUp className="h-4 w-4" />
                      Engagement
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm">Score:</span>
                      <span
                        className={`text-sm font-bold ${getScoreColor(analyses.engagement.score)}`}
                      >
                        {analyses.engagement.score}/10
                      </span>
                    </div>
                    {analyses.engagement.strengths.length > 0 && (
                      <div className="space-y-1">
                        <span className="text-xs font-medium text-green-600">
                          Strengths:
                        </span>
                        <ul className="text-xs space-y-1">
                          {analyses.engagement.strengths.map((strength, i) => (
                            <li key={i} className="flex items-start gap-2">
                              <CheckCircle2 className="h-3 w-3 text-green-600 mt-0.5" />
                              <span>{strength}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {analyses.engagement.improvements.length > 0 && (
                      <div className="space-y-1">
                        <span className="text-xs font-medium text-amber-600">
                          Improvements:
                        </span>
                        <ul className="text-xs space-y-1">
                          {analyses.engagement.improvements.map(
                            (improvement, i) => (
                              <li key={i} className="flex items-start gap-2">
                                <span className="text-muted-foreground">•</span>
                                <span>{improvement}</span>
                              </li>
                            )
                          )}
                        </ul>
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            <TabsContent value="improve" className="space-y-4">
              <div className="space-y-2">
                <Label>Improvement Type</Label>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { value: "clarity", label: "Clarity" },
                    { value: "engagement", label: "Engagement" },
                    { value: "conciseness", label: "Conciseness" },
                    { value: "professionalism", label: "Professional" },
                    { value: "seo", label: "SEO" },
                  ].map((type) => (
                    <Button
                      key={type.value}
                      variant={
                        selectedImprovementType === type.value
                          ? "default"
                          : "outline"
                      }
                      size="sm"
                      onClick={() => setSelectedImprovementType(type.value)}
                    >
                      {type.label}
                    </Button>
                  ))}
                </div>

                <Button
                  onClick={() => improveContent(selectedImprovementType)}
                  disabled={improving}
                  className="w-full"
                >
                  {improving ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Improving...
                    </>
                  ) : (
                    <>
                      <Sparkles className="h-4 w-4 mr-2" />
                      Improve Content
                    </>
                  )}
                </Button>
              </div>

              {improvedContent && (
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm">Improved Version</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <Textarea
                      value={improvedContent}
                      onChange={(e) => setImprovedContent(e.target.value)}
                      rows={8}
                      className="text-sm"
                    />
                    {changesSummary && (
                      <div className="p-2 bg-muted rounded-md">
                        <p className="text-xs font-medium mb-1">Changes:</p>
                        <p className="text-xs text-muted-foreground">
                          {changesSummary}
                        </p>
                      </div>
                    )}
                    <Button
                      onClick={applyImprovedContent}
                      disabled={!onContentChange}
                      className="w-full"
                    >
                      <CheckCircle2 className="h-4 w-4 mr-2" />
                      Apply to Editor
                    </Button>
                  </CardContent>
                </Card>
              )}
            </TabsContent>
          </Tabs>
        </div>
      </ScrollArea>
    </div>
  );
}
