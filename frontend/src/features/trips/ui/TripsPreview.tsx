import { Button } from '@/shared/ui';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui';
import { Calendar, MapPin } from 'lucide-react';

export const TripsPreview = () => {
  return (
    <div className="space-y-6">
      <Card className="bg-gradient-to-br from-primary/5 to-primary/10 border-primary/20">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <MapPin className="h-5 w-5 text-primary" /> Ближайшие поездки
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-6 text-muted-foreground">
            <Calendar className="mr-2 h-10 w-10 mx-auto mb-3 opacity-50" />
            <p>Поездок пока нет</p>
            <Button className="mt-4" size="sm">Спланировать первую поездку</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
