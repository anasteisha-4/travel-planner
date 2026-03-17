import { AppPageHeader, PageContent, PageLayout } from './page-layout';

type AuthFormProps = {
  title: string;
  description: string;
  children: React.ReactNode;
  onSubmit: (e: React.FormEvent) => void;
  onYandexLogin: () => void;
  footerText: string;
  footerLinkText: string;
  onFooterLinkClick: () => void;
  isLoading: boolean;
};

export const AuthForm = ({
  title,
  description,
  children,
  onSubmit,
  onYandexLogin,
  footerText,
  footerLinkText,
  onFooterLinkClick,
  isLoading,
}: AuthFormProps) => {
  return (
    <PageLayout fullScreen>
      <AppPageHeader pb="pb-6" className="flex flex-col items-center">
        <img
          src="/assets/logo.png"
          alt="Triply"
          className="mb-4 h-16 w-16 object-contain drop-shadow-sm"
        />
        <h1 className="text-center text-[22px] font-extrabold tracking-tight text-stone-900 dark:text-white">
          {title}
        </h1>
        <p className="mt-1 text-center text-[14px] font-medium text-stone-400 dark:text-stone-500">
          {description}
        </p>
      </AppPageHeader>

      <PageContent pb="pb-4">
        <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
          {children}
        </form>

        <div className="my-5 flex items-center gap-3">
          <div className="h-px flex-1 bg-stone-100 dark:bg-stone-800" />
          <span className="text-[11px] font-bold uppercase tracking-widest text-stone-300 dark:text-stone-600">
            или
          </span>
          <div className="h-px flex-1 bg-stone-100 dark:bg-stone-800" />
        </div>

        <button
          type="button"
          onClick={onYandexLogin}
          disabled={isLoading}
          className="flex h-[52px] w-full items-center justify-center gap-2.5 rounded-2xl border border-[#FC3F1D]/25 bg-[#FC3F1D]/10 text-[15px] font-semibold text-[#FC3F1D] transition-all active:bg-[#FC3F1D]/20 disabled:opacity-50"
        >
          <img src="/assets/yandex.png" alt="Yandex" className="h-4 w-4 object-contain" />
          Продолжить с Яндекс ID
        </button>
      </PageContent>

      <div
        className="shrink-0 border-t border-stone-100 px-5 py-4 text-center dark:border-stone-800"
        style={{ paddingBottom: 'max(env(safe-area-inset-bottom, 0px), 20px)' }}
      >
        <p className="text-[14px] text-stone-400 dark:text-stone-500">
          {footerText}{' '}
          <button type="button" onClick={onFooterLinkClick} className="font-semibold text-primary">
            {footerLinkText}
          </button>
        </p>
      </div>
    </PageLayout>
  );
};
