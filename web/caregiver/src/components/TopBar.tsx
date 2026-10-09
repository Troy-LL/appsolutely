import type { Lang } from '../types'
import type { T } from '../i18n/i18n'
import { Globe } from './Icons'
import { LangOptions } from './bits'

interface Props {
  t: T
  lang: Lang
  langOpen: boolean
  fake: boolean
  me: string
  onToggleLang: () => void
  onPickLang: (l: Lang) => void
  onAccount: () => void
}

export function TopBar({ t, lang, langOpen, fake, me, onToggleLang, onPickLang, onAccount }: Props) {
  const langName = lang === 'tl' ? 'Tagalog' : lang === 'en' ? 'English' : 'Pareho'
  return (
    <>
      <header className="sn-top">
        <p className="sn-word">
          <img src={`${import.meta.env.BASE_URL}sino-logo.webp`} alt="Sino" />
          {fake ? <span className="sn-fake">{t.one('fakeFeed')}</span> : null}
        </p>
        <div className="sn-top__tools">
          <button type="button" className={`sn-pill${langOpen ? ' is-on' : ''}`} onClick={onToggleLang}
            aria-expanded={langOpen} aria-label={t.one('a11yLang')}>
            <Globe />{langName}
          </button>
          <button type="button" className="sn-me" onClick={onAccount} aria-label={t.one('a11yAccount')}>
            <span>{me[0]?.toUpperCase()}</span>
          </button>
        </div>
      </header>
      {langOpen ? (
        <div className="sn-langpop" role="dialog" aria-label={t.one('lang')}>
          <p className="sn-langpop__t">{t.one('lang')}</p>
          <LangOptions t={t} lang={lang} onPick={onPickLang} />
        </div>
      ) : null}
    </>
  )
}
