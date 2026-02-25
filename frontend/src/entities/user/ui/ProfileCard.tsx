import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/shared/ui';
import { Mail, User } from 'lucide-react';
import type { UserProfile } from '../model/types';

export const ProfileCard = ({ profile }: { profile: UserProfile }) => {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-xl flex items-center gap-2">
          <User className="h-5 w-5 text-primary" /> Профиль
        </CardTitle>
        <CardDescription>Ваши данные</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 flex flex-col">
        <div className="flex justify-between border-b pb-2">
          <span className="text-muted-foreground font-medium text-sm">Логин</span>
          <span className="font-semibold text-primary">{profile.login}</span>
        </div>
        <div className="flex justify-between pt-2">
          <span className="text-muted-foreground font-medium text-sm flex items-center gap-2">
            <Mail className="h-4 w-4" /> Email
          </span>
          <span>{profile.email}</span>
        </div>
      </CardContent>
    </Card>
  );
};
