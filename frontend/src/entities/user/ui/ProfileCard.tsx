import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/shared/ui';
import { Mail, User } from 'lucide-react';
import type { UserProfile } from '../model/types';

export const ProfileCard = ({ profile }: { profile: UserProfile }) => {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-xl">
          <User className="h-5 w-5 text-primary" /> Профиль
        </CardTitle>
        <CardDescription>Ваши данные</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col space-y-4">
        <div className="flex justify-between border-b pb-2">
          <span className="text-sm font-medium text-muted-foreground">Логин</span>
          <span className="font-semibold text-primary">{profile.login}</span>
        </div>
        <div className="flex justify-between pt-2">
          <span className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
            <Mail className="h-4 w-4" /> Email
          </span>
          <span>{profile.email}</span>
        </div>
      </CardContent>
    </Card>
  );
};
