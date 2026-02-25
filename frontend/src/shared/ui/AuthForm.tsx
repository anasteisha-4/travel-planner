import { Button } from '@/shared/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/shared/ui/card';
import { Separator } from '@/shared/ui/separator';

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
  isLoading
}: AuthFormProps) => {
  return (
    <div className="flex flex-1 items-center justify-center p-4">
      <Card className="w-full max-w-md mx-auto glass-card">
        <CardHeader className="space-y-3 text-center">
          <div className="mx-auto flex items-center justify-center">
            <img src="/assets/logo.png" alt="Triply Logo" className="h-20 w-20 object-contain drop-shadow-md" />
          </div>
          <CardTitle className="text-2xl font-bold tracking-tight">{title}</CardTitle>
          <CardDescription>{description}</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="space-y-4" noValidate>
            {children}
          </form>
          
          <div className="my-6 flex items-center">
            <Separator className="flex-1 opacity-50" />
            <span className="mx-4 text-xs text-muted-foreground uppercase tracking-wider font-semibold">
              Или продолжить через
            </span>
            <Separator className="flex-1 opacity-50" />
          </div>
          
          <Button 
            type="button"
            variant="outline" 
            className="w-full bg-[#FC3F1D]/10 active:bg-[#FC3F1D]/20 text-[#FC3F1D] border-[#FC3F1D]/20 transition-all group backdrop-blur-sm" 
            onClick={onYandexLogin}
            disabled={isLoading}
          >
            <img src="/assets/yandex.png" alt="Yandex" className="h-4 w-4 object-contain" />
            Яндекс ID
          </Button>
        </CardContent>
        <CardFooter className="flex flex-col space-y-4">
          <div className="text-center text-sm text-muted-foreground">
            {footerText}{' '}
            <Button 
              variant="link"
              type="button"
              onClick={onFooterLinkClick} 
              className="text-primary font-medium text-base p-0 h-auto"
            >
              {footerLinkText}
            </Button>
          </div>
        </CardFooter>
      </Card>
    </div>
  );
};
