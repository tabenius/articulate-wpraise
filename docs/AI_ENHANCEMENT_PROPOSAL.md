# AI Enhancement Proposal: User-Configurable AI Experience

## Executive Summary

This proposal outlines enhancements to the Articulate platform's AI integration, allowing users to configure their AI experience through preferences, presets, and contextual AI assistance throughout the WordPress management workflow.

---

## Current State

### Existing AI Features
- ✅ Chat interface with Claude Sonnet 4.5
- ✅ WordPress tool calling (posts, blocks, media)
- ✅ Streaming responses with SSE
- ✅ BYOK (Bring Your Own Key) support
- ✅ Tool execution visualization
- ✅ Context awareness (current post/page)

### Limitations
- ❌ No AI preferences/personalization
- ❌ Limited content generation features
- ❌ No AI writing style configuration
- ❌ Manual SEO optimization only
- ❌ No AI-assisted image workflows
- ❌ No content improvement suggestions
- ❌ Chat-only AI interaction (not integrated into workflows)

---

## Proposed Enhancements

## 1. AI Preferences System

### A. User Profile AI Settings
**Location**: New settings panel under User Profile

**Configurable Options**:

```typescript
interface AIPreferences {
  // Writing Style
  tone: 'professional' | 'casual' | 'friendly' | 'authoritative' | 'conversational';
  audience: 'general' | 'technical' | 'beginner' | 'expert' | 'children';
  writingLevel: 'simple' | 'moderate' | 'advanced' | 'academic';

  // Content Generation
  contentLength: 'concise' | 'medium' | 'detailed' | 'comprehensive';
  useEmojis: boolean;
  includeSources: boolean;

  // SEO
  autoGenerateSEO: boolean;
  seoStyle: 'clickbait' | 'informative' | 'balanced' | 'conservative';
  targetKeywordDensity: number; // 1-3%

  // Language
  primaryLanguage: string; // en, es, fr, de, etc.
  translationLanguages: string[];

  // Brand Voice
  brandVoice?: string; // Custom instructions
  companyValues?: string[];
  avoidWords?: string[];
  preferredTerms?: Record<string, string>;

  // Image AI
  autoGenerateAltText: boolean;
  altTextStyle: 'descriptive' | 'concise' | 'SEO-focused';

  // Assistance Level
  suggestionFrequency: 'aggressive' | 'balanced' | 'minimal' | 'off';
  confirmBeforeApply: boolean;
}
```

### B. Organization-Level AI Settings
**Location**: Organization Settings → AI Configuration

**Features**:
- Override user preferences for consistency
- Shared brand voice across team
- Custom AI instructions for organization
- Usage limits and quotas per user
- Approved tone/style guidelines

### C. Storage Strategy
- **User preferences**: `wp_user_ai_preferences` table
- **Org settings**: `wp_org_ai_settings` table
- **Frontend cache**: localStorage with backend sync
- **Migration**: Default values for existing users

---

## 2. Contextual AI Features

### A. SEO Content Generator
**Location**: SEO Editor panel (existing component)

**Features**:
1. **Auto-Generate Meta Title**
   - Button: "Generate with AI" next to title field
   - Uses post title + content + focus keyword
   - Respects character limits (60 chars)
   - Multiple suggestions (3 options)

2. **Meta Description Generator**
   - Analyzes full post content
   - Extracts key points
   - Optimizes for 155-160 characters
   - Includes focus keyword naturally

3. **Focus Keyword Suggestions**
   - Analyzes content semantically
   - Suggests 3-5 relevant keywords
   - Shows search volume estimates (if API available)
   - Highlights keyword placement opportunities

4. **Open Graph Optimization**
   - Generates engaging OG titles (different from meta title)
   - Creates compelling OG descriptions
   - Suggests optimal OG image from media library

**UI Enhancement**:
```tsx
<div className="seo-field">
  <Label>Meta Title</Label>
  <div className="flex gap-2">
    <Input value={metaTitle} onChange={...} />
    <Button onClick={generateMetaTitle} variant="outline">
      <Sparkles className="mr-2" />
      Generate
    </Button>
  </div>
  {suggestions && (
    <div className="suggestions">
      {suggestions.map(s => (
        <SuggestionChip onClick={() => apply(s)}>{s}</SuggestionChip>
      ))}
    </div>
  )}
</div>
```

### B. Content Improvement Assistant
**Location**: New sidebar panel in Post Editor

**Features**:
1. **Grammar & Spelling**
   - Real-time analysis
   - Inline suggestions
   - Click to apply fixes

2. **Readability Score**
   - Flesch-Kincaid grade level
   - Average sentence length
   - Passive voice detection
   - Suggestions for improvement

3. **Tone Analyzer**
   - Detects current tone
   - Compares to user preference
   - Suggests adjustments
   - "Make more [friendly/professional/casual]" buttons

4. **Content Expansion**
   - "Expand this section" button on blocks
   - "Add supporting details"
   - "Add examples"
   - "Add statistics/data"

5. **Content Summarization**
   - Auto-generate TL;DR
   - Extract key points
   - Create bullet list summaries

**UI Component**:
```tsx
<ContentAssistant>
  <Tab label="Improve">
    <ReadabilityScore score={85} grade="8th grade" />
    <ToneMatch current="professional" target="friendly" />
    <GrammarSuggestions count={3} />
  </Tab>
  <Tab label="Expand">
    <Button>Add Introduction</Button>
    <Button>Add Conclusion</Button>
    <Button>Add Examples</Button>
  </Tab>
  <Tab label="Optimize">
    <SEOScore score={72} />
    <KeywordDensity keyword="AI tools" density={1.2} />
  </Tab>
</ContentAssistant>
```

### C. Image AI Tools
**Location**: Media Library & Image Optimizer

**Features**:
1. **Auto Alt Text Generation**
   - Analyze image with Claude + vision
   - Generate descriptive alt text
   - SEO-optimized or accessibility-focused
   - Batch processing for media library

2. **Smart Image Tagging**
   - Detect objects, scenes, concepts
   - Auto-suggest WordPress media tags
   - Organize media library

3. **Image Selection Assistant**
   - "Find image for this block" button
   - Analyzes block content
   - Suggests relevant images from library
   - Shows similarity scores

4. **Caption Generation**
   - Generate engaging captions
   - Match brand voice
   - Include keywords naturally

**Implementation**:
```typescript
async function generateAltText(imageUrl: string, style: 'descriptive' | 'seo') {
  const preferences = await getAIPreferences();

  const prompt = style === 'seo'
    ? `Generate SEO-optimized alt text for this image. Include relevant keywords naturally.`
    : `Generate accessible, descriptive alt text for visually impaired users.`;

  const response = await claude.messages.create({
    model: 'claude-3-5-sonnet-20241022',
    max_tokens: 100,
    messages: [{
      role: 'user',
      content: [
        { type: 'image', source: { type: 'url', url: imageUrl } },
        { type: 'text', text: prompt }
      ]
    }]
  });

  return response.content[0].text;
}
```

### D. Template & Block Suggestions
**Location**: Site Editor & Template Manager

**Features**:
1. **Template Generation**
   - "Create template from description"
   - Input: "Product page with hero, features, testimonials"
   - Output: Complete block structure

2. **Block Recommendations**
   - Suggests next logical block based on context
   - "Readers also added: [Image Gallery] [CTA Button] [FAQ]"
   - Smart defaults based on post type

3. **Layout Optimization**
   - Analyze existing layout
   - Suggest improvements
   - A/B test variants

---

## 3. AI Writing Modes

### A. Quick Actions Palette
**Location**: Editor toolbar (keyboard shortcut: Cmd+K)

**Features**:
- Command palette with AI actions
- Fuzzy search
- Recently used actions
- Customizable shortcuts

**Commands**:
```
- "Improve writing" → Enhance selected text
- "Make it shorter" → Condense content
- "Make it longer" → Expand content
- "Change tone to [X]" → Adjust tone
- "Translate to [language]" → Translation
- "Generate outline" → Create structure
- "Add examples" → Insert examples
- "Fix grammar" → Correct errors
- "Simplify" → Reduce complexity
```

### B. Block-Level AI
**Location**: Block toolbar (appears on hover)

**Features**:
- AI button on each block
- Context menu with actions
- Inline editing with AI

**Actions per Block Type**:

**Paragraph Block**:
- Rewrite in different tone
- Expand with details
- Shorten
- Add bullet points
- Convert to list

**Heading Block**:
- Suggest alternatives (5 options)
- SEO optimize
- Improve clarity

**List Block**:
- Add more items
- Convert to paragraph
- Prioritize by importance

**Image Block**:
- Generate alt text
- Generate caption
- Suggest better image from library

**Code Block**:
- Explain code
- Add comments
- Suggest improvements

### C. AI Workflows
**Location**: New "Workflows" menu

**Pre-built Workflows**:

1. **Blog Post from Outline**
   - Input: Bullet point outline
   - Output: Fully written post with intro, body, conclusion
   - Includes headings, paragraphs, lists

2. **Product Description Generator**
   - Input: Product name, features, specs
   - Output: Compelling product description
   - Includes benefits, use cases, CTA

3. **SEO Content Optimizer**
   - Input: Existing post
   - Output: Optimized version with:
     - Better keyword placement
     - Improved readability
     - Enhanced meta tags
     - Suggested internal links

4. **Social Media Content**
   - Input: Blog post URL
   - Output:
     - Twitter thread
     - LinkedIn post
     - Facebook description
     - Instagram caption

5. **Multi-language Publisher**
   - Input: Post in primary language
   - Output: Translated posts in configured languages
   - Maintains formatting and structure

---

## 4. Smart Suggestions System

### A. Proactive Assistance
**Triggers**:
- User pauses typing for 3 seconds
- User selects text
- User creates new block
- User navigates to new section

**Suggestion Types**:

1. **Writing Improvements**
   ```
   💡 Suggestion: This paragraph could be clearer
   [Show rewrite] [Dismiss]
   ```

2. **SEO Opportunities**
   ```
   🎯 SEO Tip: Add your focus keyword "AI tools" here
   [Apply] [Ignore]
   ```

3. **Content Gaps**
   ```
   📝 Consider adding:
   - Examples of AI tools
   - Comparison table
   - User testimonials
   [Generate] [Skip]
   ```

4. **Readability Alerts**
   ```
   📊 Readability: This sentence is complex (grade 12)
   Target: Grade 8
   [Simplify] [Keep as is]
   ```

### B. Suggestion Settings
**Configuration**:
```typescript
interface SuggestionSettings {
  enabled: boolean;
  frequency: 'high' | 'medium' | 'low';
  categories: {
    grammar: boolean;
    seo: boolean;
    readability: boolean;
    content: boolean;
    style: boolean;
  };
  dismissedSuggestions: string[]; // Never show again
  autoApply: boolean; // Apply without confirmation
}
```

---

## 5. AI Model Selection

### A. Model Picker
**Location**: Settings → AI Configuration

**Options**:
- **Claude Sonnet 4.5** (Default - Balanced)
- **Claude Opus 4** (Premium - Highest quality)
- **Claude Haiku 4** (Fast - Quick responses)

**Per-Feature Configuration**:
```typescript
interface ModelConfig {
  chat: 'sonnet' | 'opus' | 'haiku';
  contentGeneration: 'sonnet' | 'opus' | 'haiku';
  seoOptimization: 'sonnet' | 'opus' | 'haiku';
  imageAnalysis: 'sonnet' | 'opus' | 'haiku';
  translation: 'sonnet' | 'opus' | 'haiku';
}
```

**Cost Display**:
- Show estimated costs per 1000 requests
- Monthly usage tracking
- Budget alerts

### B. Prompt Engineering UI
**Location**: Advanced Settings

**Features**:
- View default system prompts
- Add custom instructions
- Test prompts in playground
- Version control for prompts
- Share prompts with team

---

## 6. Integration Points

### A. Keyboard Shortcuts
```
Cmd+K          → Open AI command palette
Cmd+Shift+I    → Improve selected text
Cmd+Shift+E    → Expand selected text
Cmd+Shift+S    → SEO optimize
Cmd+Shift+T    → Translate
Cmd+Shift+G    → Generate continuation
```

### B. Context Menu
Right-click on any text:
- AI: Improve writing
- AI: Change tone
- AI: Translate
- AI: Explain
- AI: Generate more

### C. Floating Toolbar
When text is selected, show floating toolbar:
```
[B] [I] [U] | [🤖 AI ▼]
                └─ Improve
                   Expand
                   Summarize
                   Change tone
                   Translate
```

---

## 7. Database Schema

### User AI Preferences
```sql
CREATE TABLE wp_user_ai_preferences (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id BIGINT UNSIGNED NOT NULL,

  -- Writing Style
  tone VARCHAR(50) DEFAULT 'professional',
  audience VARCHAR(50) DEFAULT 'general',
  writing_level VARCHAR(50) DEFAULT 'moderate',
  content_length VARCHAR(50) DEFAULT 'medium',

  -- SEO
  auto_generate_seo BOOLEAN DEFAULT false,
  seo_style VARCHAR(50) DEFAULT 'balanced',
  target_keyword_density DECIMAL(3,1) DEFAULT 1.5,

  -- Language
  primary_language VARCHAR(10) DEFAULT 'en',
  translation_languages JSON,

  -- Brand Voice
  brand_voice TEXT,
  company_values JSON,
  avoid_words JSON,
  preferred_terms JSON,

  -- Image AI
  auto_generate_alt_text BOOLEAN DEFAULT true,
  alt_text_style VARCHAR(50) DEFAULT 'descriptive',

  -- Suggestions
  suggestion_frequency VARCHAR(50) DEFAULT 'balanced',
  confirm_before_apply BOOLEAN DEFAULT true,
  dismissed_suggestions JSON,

  -- Model Selection
  default_model VARCHAR(50) DEFAULT 'sonnet',
  model_config JSON,

  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  FOREIGN KEY (user_id) REFERENCES wp_users(id) ON DELETE CASCADE,
  UNIQUE KEY unique_user (user_id)
);
```

### Organization AI Settings
```sql
CREATE TABLE wp_org_ai_settings (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  organization_id BIGINT UNSIGNED NOT NULL,

  -- Override user preferences
  enforce_brand_voice BOOLEAN DEFAULT false,
  brand_voice TEXT,
  tone VARCHAR(50),
  writing_level VARCHAR(50),

  -- Usage Limits
  monthly_request_limit INT,
  cost_limit_usd DECIMAL(10,2),

  -- Shared Resources
  custom_prompts JSON,
  approved_styles JSON,

  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  FOREIGN KEY (organization_id) REFERENCES articulate_organizations(id) ON DELETE CASCADE,
  UNIQUE KEY unique_org (organization_id)
);
```

### AI Usage Tracking
```sql
CREATE TABLE articulate_ai_usage (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id BIGINT UNSIGNED NOT NULL,
  organization_id BIGINT UNSIGNED,

  feature VARCHAR(100) NOT NULL, -- 'chat', 'seo_generation', 'content_improve', etc.
  model VARCHAR(50) NOT NULL,

  input_tokens INT NOT NULL,
  output_tokens INT NOT NULL,
  cost_usd DECIMAL(10,6),

  request_data JSON, -- Store request details
  response_data JSON, -- Store response details

  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

  FOREIGN KEY (user_id) REFERENCES wp_users(id) ON DELETE CASCADE,
  FOREIGN KEY (organization_id) REFERENCES articulate_organizations(id) ON DELETE SET NULL,

  INDEX idx_user_date (user_id, created_at),
  INDEX idx_org_date (organization_id, created_at)
);
```

---

## 8. UI Components

### A. AI Preferences Panel
**Component**: `<AIPreferencesPanel />`
**Location**: User Settings → AI Preferences

```tsx
import { Card, Tabs, Select, Switch, Textarea } from '@/components/ui';

export function AIPreferencesPanel() {
  const [prefs, setPrefs] = useState<AIPreferences>();

  return (
    <Card>
      <Tabs>
        <Tab label="Writing Style">
          <Select label="Tone" value={prefs.tone} options={toneOptions} />
          <Select label="Audience" value={prefs.audience} options={audienceOptions} />
          <Select label="Writing Level" value={prefs.writingLevel} options={levelOptions} />
        </Tab>

        <Tab label="Brand Voice">
          <Textarea
            label="Custom Instructions"
            placeholder="Write content in first person, use conversational tone..."
            value={prefs.brandVoice}
          />
          <TagInput label="Avoid Words" value={prefs.avoidWords} />
        </Tab>

        <Tab label="SEO">
          <Switch label="Auto-generate SEO" checked={prefs.autoGenerateSEO} />
          <Select label="SEO Style" value={prefs.seoStyle} />
          <Slider label="Keyword Density" value={prefs.targetKeywordDensity} min={1} max={3} />
        </Tab>

        <Tab label="Models">
          <ModelSelector config={prefs.modelConfig} />
          <UsageStats userId={user.id} />
        </Tab>
      </Tabs>
    </Card>
  );
}
```

### B. Content Assistant Sidebar
**Component**: `<ContentAssistantSidebar />`
**Location**: Post Editor → Right Sidebar

```tsx
export function ContentAssistantSidebar({ postId }: { postId: number }) {
  return (
    <aside className="content-assistant">
      <Tabs>
        <Tab label="Improve" icon={<Sparkles />}>
          <ReadabilityCard score={readability} />
          <GrammarCard issues={grammarIssues} />
          <ToneCard current="professional" target="friendly" />
        </Tab>

        <Tab label="SEO" icon={<Target />}>
          <SEOScoreCard score={seoScore} />
          <KeywordCard keywords={keywords} />
          <MetaPreview title={metaTitle} description={metaDescription} />
        </Tab>

        <Tab label="Expand" icon={<PlusCircle />}>
          <SuggestionsList suggestions={contentSuggestions} />
          <Button onClick={generateConclusion}>Add Conclusion</Button>
        </Tab>
      </Tabs>
    </aside>
  );
}
```

### C. AI Command Palette
**Component**: `<AICommandPalette />`
**Shortcut**: Cmd+K

```tsx
export function AICommandPalette() {
  const [open, setOpen] = useState(false);

  useHotkey('cmd+k', () => setOpen(true));

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput placeholder="Type a command or search..." />
      <CommandList>
        <CommandGroup heading="AI Actions">
          <CommandItem onSelect={improveWriting}>
            <Sparkles className="mr-2" />
            Improve writing
          </CommandItem>
          <CommandItem onSelect={generateSEO}>
            <Target className="mr-2" />
            Generate SEO meta tags
          </CommandItem>
          <CommandItem onSelect={translate}>
            <Languages className="mr-2" />
            Translate to...
          </CommandItem>
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}
```

---

## 9. Implementation Phases

### Phase 1: Foundation (2 weeks)
- ✅ Database schema migration
- ✅ AI preferences backend API
- ✅ Settings UI for preferences
- ✅ Basic preference application in chat

### Phase 2: SEO Enhancement (1 week)
- ✅ SEO content generation
- ✅ Meta title/description generator
- ✅ Keyword suggestions
- ✅ Integration with existing SEO editor

### Phase 3: Content Assistant (2 weeks)
- ✅ Content improvement sidebar
- ✅ Readability analyzer
- ✅ Grammar checker
- ✅ Tone analyzer
- ✅ Block-level AI actions

### Phase 4: Image AI (1 week)
- ✅ Alt text generation
- ✅ Batch processing
- ✅ Image tagging
- ✅ Smart image suggestions

### Phase 5: Advanced Features (2 weeks)
- ✅ AI command palette
- ✅ Workflows system
- ✅ Template generation
- ✅ Multi-language support

### Phase 6: Analytics & Optimization (1 week)
- ✅ Usage tracking
- ✅ Cost monitoring
- ✅ Performance metrics
- ✅ User feedback collection

---

## 10. Success Metrics

### User Engagement
- % of users enabling AI preferences
- Average AI interactions per session
- Feature adoption rates
- User satisfaction scores

### Content Quality
- Average readability scores (before/after)
- SEO scores improvement
- Time saved per post
- Grammar error reduction

### Business Impact
- User retention improvement
- Premium feature conversion
- API cost per user
- Support ticket reduction

---

## Conclusion

These enhancements transform Articulate from a chat-based AI assistant into a comprehensive, personalized AI-powered content platform. Users gain control over AI behavior through preferences while benefiting from contextual AI assistance throughout their workflow.

**Key Differentiators**:
- 🎯 User-configurable AI experience
- 🚀 Context-aware suggestions
- 🎨 Brand voice consistency
- 📊 Transparent usage tracking
- 🌍 Multi-language support
- ⚡ Integrated throughout UI (not just chat)

This positions Articulate as the most advanced AI-powered WordPress management platform available.
