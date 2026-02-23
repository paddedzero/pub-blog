export interface SiteConfig {
  author: string;
  desc: string;
  title: string;
  ogImage: string;
  lang: string;
  base: string;
  website: string;
  social: Record<string, string>;
  googleAnalyticsId?: string;
  homeHeroDescription: string;
  blogDescription: string;
  projectsDescription: string;
  featuredPostsCount: number;
  latestPostsCount: number;
  homeProjects: {
    enabled: boolean;
    count: number;
  };
  cta: {
    enabled: boolean;
    filePath: string;
  };
  hero: {
    enabled: boolean;
    filePath: string;
  };
  comments: {
    enabled: boolean;
    repo: string;
    repoId: string;
    category: string;
    categoryId: string;
    mapping: 'pathname' | 'url' | 'title' | 'og:title' | 'specific' | 'number';
    reactionsEnabled: boolean;
    emitMetadata: boolean;
    inputPosition: 'top' | 'bottom';
    theme: string;
    lang: string;
  };
}

export const SITE: SiteConfig = {
  author: 'paddedzero',
  desc: 'Automated news aggregation for Cloud, Cybersecurity, AI, and ML technologies.',
  title: 'pub-blog',
  ogImage: 'og.png',
  lang: 'en-US',
  base: '/pub-blog/',
  website: 'https://paddedzero.github.io/pub-blog',
  social: {
    github: 'https://github.com/paddedzero',
  },
  googleAnalyticsId: '',
  homeHeroDescription:
    'Weekly automated news aggregation covering Cloud computing, Cybersecurity, AI, and Machine Learning. Powered by RSS feeds and AI summarization.',
  blogDescription: 'Weekly news briefs and analyst opinions on Cloud, Cybersecurity, AI, and ML.',
  projectsDescription: '',

  featuredPostsCount: 1,
  latestPostsCount: 5,

  homeProjects: {
    enabled: false,
    count: 0,
  },

  cta: {
    enabled: false,
    filePath: 'site/cta.md',
  },

  hero: {
    enabled: true,
    filePath: 'site/hero.md',
  },

  comments: {
    enabled: false,
    repo: 'paddedzero/pub-blog',
    repoId: '',
    category: 'General',
    categoryId: '',
    mapping: 'pathname',
    reactionsEnabled: true,
    emitMetadata: false,
    inputPosition: 'bottom',
    theme: 'preferred_color_scheme',
    lang: 'en',
  },
};
