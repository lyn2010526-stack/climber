import { useEffect, useState } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { Bot, MessageSquare, Settings } from 'lucide-react';
import { ClimberMark } from '../brand/ClimberMark';
import { MagneticPress } from '../motion/MagneticPress';
import { useBootReveal } from '../motion/bootHandoff';
import { Button } from '../ui/Button';
import { useI18n } from '../../i18n/utils';
import { hasHeroIntroPlayed, markHeroIntroPlayed } from './heroIntro';
import './hero.css';

const heroContainerVariants = {
  hidden: {},
  visible: { transition: { delayChildren: 0.08, staggerChildren: 0.12 } },
};

const heroItemVariants = {
  hidden: { opacity: 0, y: 18 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.45, ease: [0.16, 1, 0.3, 1] as [number, number, number, number] },
  },
};

export function HeroSection() {
  const { t } = useI18n();
  const reducedMotion = useReducedMotion();
  const [playIntro] = useState(() => !hasHeroIntroPlayed());
  // The hero mounts underneath the splash from the first frame, so it cannot
  // spend its intro on mount: the gesture would be over by the time the curtain
  // lifts. Hold it in the opening state until the boot announces the reveal,
  // then start — the entrance is spent in view instead of behind the curtain.
  const revealed = useBootReveal();

  useEffect(() => {
    markHeroIntroPlayed();
  }, []);

  const instant = Boolean(reducedMotion) || !playIntro;

  return (
    <motion.section
      aria-label={t('hero.label', { defaultValue: 'Climber 主视觉区' })}
      data-hero-intro={instant ? 'instant' : 'play'}
      variants={heroContainerVariants}
      initial={instant ? false : 'hidden'}
      animate={instant || revealed ? 'visible' : 'hidden'}
      className="relative mb-[var(--space-5)] overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-border-default)] bg-[var(--color-bg-surface-1)] shadow-[var(--shadow-panel)]"
    >
      <span aria-hidden="true" className="hero-glow" />
      <span aria-hidden="true" className="hero-grid" />
      <span aria-hidden="true" className="hero-watermark">
        <ClimberMark size={272} color="currentColor" strokeWidth={1.2} />
      </span>

      <div className="relative flex flex-col gap-[var(--space-4)] p-[var(--space-6)] sm:p-[var(--space-8)]">
        <motion.span
          variants={heroItemVariants}
          data-hero-item="mark"
          className="flex h-[52px] w-[52px] items-center justify-center rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] bg-[var(--color-accent-subtle)] text-[var(--color-accent-foreground)]"
        >
          <ClimberMark size={28} />
        </motion.span>

        <div className="flex flex-col gap-[var(--space-1-5)]">
          <motion.h1
            variants={heroItemVariants}
            data-hero-item="title"
            className="text-[length:var(--text-2xl)] font-semibold leading-[var(--leading-tight)] tracking-[-0.02em] text-[var(--color-text-primary)] md:text-[length:var(--text-3xl)]"
          >
            Climber
          </motion.h1>
          <motion.p
            variants={heroItemVariants}
            data-hero-item="subtitle"
            className="max-w-[36rem] text-[length:var(--text-sm)] leading-[var(--leading-relaxed)] text-[var(--color-text-secondary)]"
          >
            {t('hero.subtitle', { defaultValue: '从一次对话开始，指挥你的 Agent 集群协同完成每一次攀登。' })}
          </motion.p>
        </div>

        <motion.div
          variants={heroItemVariants}
          data-hero-item="actions"
          className="flex flex-wrap items-center gap-[var(--space-2)]"
        >
          <MagneticPress>
            <Button
              size="md"
              onClick={() => { window.location.hash = 'chat'; }}
              icon={<MessageSquare size={16} />}
              className="text-[length:13px] rounded-[var(--radius-md)]"
            >
              {t('hero.cta_chat', { defaultValue: '开始对话' })}
            </Button>
          </MagneticPress>
          <MagneticPress>
            <Button
              variant="secondary"
              size="md"
              onClick={() => { window.location.hash = 'agents'; }}
              icon={<Bot size={16} />}
              className="text-[length:13px] rounded-[var(--radius-md)]"
            >
              {t('hero.cta_agents', { defaultValue: '查看 Agent' })}
            </Button>
          </MagneticPress>
          <MagneticPress>
            <Button
              variant="ghost"
              size="md"
              onClick={() => { window.location.hash = 'settings'; }}
              icon={<Settings size={16} />}
              className="text-[length:13px] rounded-[var(--radius-md)]"
            >
              {t('hero.cta_settings', { defaultValue: '设置' })}
            </Button>
          </MagneticPress>
        </motion.div>
      </div>
    </motion.section>
  );
}

export default HeroSection;
