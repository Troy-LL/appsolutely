import type { Health, Lang, Scale } from '../types'
import type { T } from '../i18n/i18n'
import { Frame } from '../components/Frame'
import { SubHead } from '../components/SubHead'
import { Heading, LangOptions, TextScale } from '../components/bits'

interface Props {
  t: T
  me: string
  health: Health | null
  lang: Lang
  scale: Scale
  onLang: (l: Lang) => void
  onScale: (s: Scale) => void
  onBack: () => void
}

// Account: who you are, how Lola's home is doing (the health event), alerts, size, language.
export function AccountScreen({ t, me, health, lang, scale, onLang, onScale, onBack }: Props) {
  const part = (label: string, up: boolean | undefined) => (
    <li key={label}>
      <b>{label}</b>
      <span className={`sn-tag ${up ? 'sn-tag--green' : 'sn-tag--amber'}`}>{up ? `✓ ${t.one('on')}` : `● ${t.one('off')}`}</span>
    </li>
  )
  const h = (k: Parameters<T['head']>[0]) => t.head(k)
  return (
    <>
      <SubHead title={t.one('account')} label={t.one('back')} onBack={onBack} />
      <div className="sn-scroll">
        <div className="sn-profile">
          <Frame name={me} color="green" show />
          <div><h1>{me}</h1><p className="pl">{t.two('role')}</p></div>
        </div>

        <div className="sn-block">
          <Heading {...{ main: h('home').main, sub: h('home').sub }} />
          <ul className="sn-list">
            {part(t.one('boxName'), health?.server)}
            {part(t.one('partMic'), health?.mic)}
            {part(t.one('partWhisper'), health?.whisper)}
            {part(t.one('partModel'), health?.ollama)}
            <li>
              <span><b>{t.one('netName')}</b><small>{health?.offline === false ? t.one('netOnline') : t.one('netState')}</small></span>
              <span className={`sn-tag ${health?.offline === false ? 'sn-tag--amber' : 'sn-tag--ink'}`}>{health?.offline === false ? t.one('online') : t.one('offline')}</span>
            </li>
          </ul>
        </div>

        <div className="sn-block">
          <Heading main={h('alerts').main} sub={h('alerts').sub} />
          <ul className="sn-list">
            <li><span><b>▲ {t.one('urgentHead')}</b><small>{t.one('urgentAlert')}</small></span><span className="sn-lock">{t.one('always')}</span></li>
          </ul>
        </div>

        <div className="sn-block">
          <Heading main={h('size').main} sub={h('size').sub} />
          <TextScale scale={scale} onPick={onScale} />
        </div>

        <div className="sn-block">
          <Heading main={h('lang').main} sub={h('lang').sub} />
          <LangOptions t={t} lang={lang} onPick={onLang} />
        </div>
      </div>
    </>
  )
}
