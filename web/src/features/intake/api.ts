import { useQuery } from "@tanstack/react-query";
import { api } from "../../api/client";
import type { Question } from "./build";

export const useQuestions = () =>
  useQuery({ queryKey: ["questions"], queryFn: () => api.get<Question[]>("/questions"), staleTime: Infinity });
