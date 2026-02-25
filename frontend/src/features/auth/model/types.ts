import { z } from 'zod';

export const AuthResponseSchema = z.object({
  access_token: z.string(),
  refresh_token: z.string(),
  token_type: z.string(),
});

export type AuthResponse = z.infer<typeof AuthResponseSchema>;

export const AuthCredentialsSchema = z.object({
  identifier: z.string().nonempty("Введите логин или почту"),
  password: z.string().nonempty("Введите пароль"),
});

export type AuthCredentials = z.infer<typeof AuthCredentialsSchema>;

/**
 * Schema for the register API request
 */
export const RegisterApiSchema = z.object({
  login: z.string()
    .nonempty("Введите логин")
    .min(3, "Логин должен содержать минимум 3 символа")
    .regex(/^[a-zA-Z0-9_]+$/, "Только латинские буквы, цифры и подчеркивание"),
  email: z.string()
    .nonempty("Введите почту")
    .email("Введите корректную почту"),
  password: z.string()
    .nonempty("Введите пароль")
    .min(8, "Пароль должен содержать минимум 8 символов")
    .regex(
      /^(?=.*[a-zA-Zа-яА-ЯёЁ])(?=.*\d)(?=.*[^a-zA-Zа-яА-ЯёЁ0-9\s]).+$/,
      "Пароль должен содержать строчные и заглавные буквы, цифры и спецсимволы"
    ),
});

export type RegisterCredentials = z.infer<typeof RegisterApiSchema>;

/**
 * Schema for the registration form, includes confirmPassword
 */
export const RegisterFormSchema = RegisterApiSchema.extend({
  confirmPassword: z.string().nonempty("Подтвердите пароль"),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Пароли не совпадают",
  path: ["confirmPassword"],
});

export type RegisterFormData = z.infer<typeof RegisterFormSchema>;
